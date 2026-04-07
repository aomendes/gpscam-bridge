from __future__ import annotations

import asyncio
import ipaddress
import socket
from typing import Callable, Iterable

from .constants import FALLBACK_PORTS, SCAN_CONCURRENCY
from .models import Endpoint, ServerStatus
from .network_client import MobileServerClient


def _local_ipv4_addresses() -> list[str]:
    addresses: set[str] = set()

    try:
        hostname = socket.gethostname()
        _, _, ips = socket.gethostbyname_ex(hostname)
        for ip in ips:
            if ip and not ip.startswith("127."):
                addresses.add(ip)
    except OSError:
        pass

    # Captures the currently active interface used for outbound routes.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                addresses.add(ip)
    except OSError:
        pass

    return sorted(addresses)


def _candidate_networks(local_ips: Iterable[str]) -> list[ipaddress.IPv4Network]:
    networks: set[ipaddress.IPv4Network] = set()
    for ip in local_ips:
        try:
            parsed = ipaddress.IPv4Address(ip)
            networks.add(ipaddress.IPv4Network(f"{parsed}/24", strict=False))
        except ipaddress.AddressValueError:
            continue
    return sorted(networks, key=lambda n: str(n.network_address))


async def discover_server_on_local_subnets(
    client: MobileServerClient,
    preferred_port: int,
    log: Callable[[str], None],
    per_probe_timeout: float = 0.35,
) -> tuple[Endpoint, ServerStatus] | tuple[None, None]:
    local_ips = _local_ipv4_addresses()
    if not local_ips:
        log("Auto-detect: no active IPv4 interface found.")
        return None, None

    networks = _candidate_networks(local_ips)
    if not networks:
        log("Auto-detect: unable to derive local /24 subnets.")
        return None, None

    ports = [preferred_port] + [p for p in FALLBACK_PORTS if p != preferred_port]
    log(f"Auto-detect: scanning {len(networks)} subnet(s) on ports {ports[0]}..{ports[-1]}.")

    semaphore = asyncio.Semaphore(SCAN_CONCURRENCY)

    async def probe(endpoint: Endpoint) -> tuple[Endpoint, ServerStatus] | None:
        async with semaphore:
            try:
                status = await asyncio.wait_for(client.get_status(endpoint), timeout=per_probe_timeout)
                return endpoint, status
            except Exception:
                return None

    for port in ports:
        tasks: list[asyncio.Task] = []

        for network in networks:
            for host in network.hosts():
                host_str = str(host)
                if host_str in local_ips:
                    continue
                tasks.append(asyncio.create_task(probe(Endpoint(host=host_str, port=port))))

        if not tasks:
            continue

        try:
            for done in asyncio.as_completed(tasks):
                result = await done
                if result is not None:
                    for task in tasks:
                        task.cancel()
                    endpoint, status = result
                    log(f"Auto-detect: found mobile server at {endpoint.host}:{endpoint.port}.")
                    return endpoint, status
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    log("Auto-detect: no server found on local subnets.")
    return None, None
