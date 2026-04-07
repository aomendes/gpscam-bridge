from __future__ import annotations

import asyncio
import ipaddress
import time
from typing import Callable, Optional

from .constants import BACKOFF_STEPS_SECONDS, FALLBACK_PORTS, RECOVERY_TIMEOUT_SECONDS, SCAN_CONCURRENCY
from .models import Endpoint, ServerStatus
from .network_client import MobileServerClient


class EndpointRecovery:
    def __init__(
        self,
        client: MobileServerClient,
        log: Callable[[str], None],
    ) -> None:
        self._client = client
        self._log = log

    async def recover(
        self,
        initial_endpoint: Endpoint,
        expected_server_id: Optional[str],
        timeout_seconds: int = RECOVERY_TIMEOUT_SECONDS,
    ) -> tuple[Endpoint, ServerStatus] | tuple[None, None]:
        deadline = time.monotonic() + timeout_seconds
        attempt = 0

        while time.monotonic() < deadline:
            self._log(f"Recovery attempt {attempt + 1}: trying known host and fallback ports.")
            endpoint_status = await self._probe_known_host(initial_endpoint.host, expected_server_id, deadline)
            if endpoint_status is not None:
                return endpoint_status

            self._log("Known host failed. Scanning local /24 subnet for matching server_id.")
            endpoint_status = await self._scan_subnet(initial_endpoint, expected_server_id, deadline)
            if endpoint_status is not None:
                return endpoint_status

            delay = BACKOFF_STEPS_SECONDS[attempt % len(BACKOFF_STEPS_SECONDS)]
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            await asyncio.sleep(min(delay, remaining))
            attempt += 1

        return None, None

    async def _probe_known_host(
        self,
        host: str,
        expected_server_id: Optional[str],
        deadline: float,
    ) -> tuple[Endpoint, ServerStatus] | None:
        for port in FALLBACK_PORTS:
            if time.monotonic() >= deadline:
                return None
            endpoint = Endpoint(host=host, port=port)
            status = await self._safe_get_status(endpoint, timeout_seconds=min(1.2, max(deadline - time.monotonic(), 0.1)))
            if status is None:
                continue
            if expected_server_id and status.server_id != expected_server_id:
                continue
            self._log(f"Recovered connection on {endpoint.host}:{endpoint.port}.")
            return endpoint, status
        return None

    async def _scan_subnet(
        self,
        initial_endpoint: Endpoint,
        expected_server_id: Optional[str],
        deadline: float,
    ) -> tuple[Endpoint, ServerStatus] | None:
        try:
            parsed = ipaddress.IPv4Address(initial_endpoint.host)
        except ipaddress.AddressValueError:
            self._log("Initial host is not IPv4; skipping /24 scan.")
            return None

        network = ipaddress.IPv4Network(f"{parsed}/24", strict=False)
        ports = [initial_endpoint.port] + [p for p in FALLBACK_PORTS if p != initial_endpoint.port]

        for port in ports:
            if time.monotonic() >= deadline:
                return None
            tasks = []
            semaphore = asyncio.Semaphore(SCAN_CONCURRENCY)

            for host in network.hosts():
                host_str = str(host)
                if host_str == initial_endpoint.host:
                    continue
                endpoint = Endpoint(host=host_str, port=port)
                tasks.append(
                    asyncio.create_task(
                        self._probe_with_semaphore(
                            endpoint=endpoint,
                            expected_server_id=expected_server_id,
                            semaphore=semaphore,
                            deadline=deadline,
                        )
                    )
                )

            if not tasks:
                continue

            try:
                for coro in asyncio.as_completed(tasks):
                    match = await coro
                    if match is not None:
                        for task in tasks:
                            task.cancel()
                        self._log(f"Subnet scan found server on {match[0].host}:{match[0].port}.")
                        return match
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

        return None

    async def _probe_with_semaphore(
        self,
        endpoint: Endpoint,
        expected_server_id: Optional[str],
        semaphore: asyncio.Semaphore,
        deadline: float,
    ) -> tuple[Endpoint, ServerStatus] | None:
        async with semaphore:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            status = await self._safe_get_status(endpoint, timeout_seconds=min(0.4, max(remaining, 0.1)))
            if status is None:
                return None
            if expected_server_id and status.server_id != expected_server_id:
                return None
            return endpoint, status

    async def _safe_get_status(self, endpoint: Endpoint, timeout_seconds: float) -> ServerStatus | None:
        try:
            return await asyncio.wait_for(self._client.get_status(endpoint), timeout=timeout_seconds)
        except Exception:
            return None
