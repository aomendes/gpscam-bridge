from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Optional

import aiohttp

from .constants import HTTP_TIMEOUT_SECONDS
from .models import Endpoint, GpsSample, ServerStatus


class MobileServerClient:
    def __init__(self) -> None:
        timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)
        self._session = aiohttp.ClientSession(timeout=timeout)

    async def close(self) -> None:
        await self._session.close()

    async def get_status(self, endpoint: Endpoint) -> ServerStatus:
        async with self._session.get(f"{endpoint.base_url}/api/status") as response:
            response.raise_for_status()
            payload = await response.json()

        return ServerStatus(
            app_version=str(payload["app_version"]),
            server_id=str(payload["server_id"]),
            ip=str(payload["ip"]),
            port=int(payload["port"]),
            camera_state=str(payload["camera_state"]),
            gps_state=str(payload["gps_state"]),
        )

    async def check_health(self, endpoint: Endpoint) -> bool:
        try:
            async with self._session.get(f"{endpoint.base_url}/api/health") as response:
                if response.status != 200:
                    return False
                payload = await response.json()
                return bool(payload.get("ok"))
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return False

    async def gps_stream(self, endpoint: Endpoint) -> AsyncIterator[GpsSample]:
        ws_url = f"ws://{endpoint.host}:{endpoint.port}/api/gps"
        async with self._session.ws_connect(ws_url, heartbeat=20) as ws:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    yield GpsSample(
                        latitude=float(data["latitude"]),
                        longitude=float(data["longitude"]),
                        accuracy_m=float(data.get("accuracy_m", 0.0)),
                        heading_deg=(float(data["heading_deg"]) if data.get("heading_deg") is not None else None),
                        speed_mps=(float(data["speed_mps"]) if data.get("speed_mps") is not None else None),
                        timestamp_ms=int(data["timestamp_ms"]),
                    )
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    raise ws.exception() or RuntimeError("WebSocket error")

    async def wait_for_new_gps_sample(
        self,
        endpoint: Endpoint,
        after_timestamp_ms: Optional[int],
        timeout_seconds: float = 8.0,
    ) -> Optional[GpsSample]:
        async def _await_sample() -> Optional[GpsSample]:
            async for sample in self.gps_stream(endpoint):
                if after_timestamp_ms is None or sample.timestamp_ms > after_timestamp_ms:
                    return sample
            return None

        try:
            return await asyncio.wait_for(_await_sample(), timeout=timeout_seconds)
        except (asyncio.TimeoutError, aiohttp.ClientError):
            return None

    async def post_webrtc_offer(self, endpoint: Endpoint, offer: dict) -> dict:
        # Signaling endpoint required by contract. App currently uses status only.
        async with self._session.post(f"{endpoint.base_url}/api/webrtc/offer", json=offer) as response:
            response.raise_for_status()
            return await response.json()

    async def post_webrtc_ice(self, endpoint: Endpoint, candidate: dict) -> dict:
        async with self._session.post(f"{endpoint.base_url}/api/webrtc/ice", json=candidate) as response:
            response.raise_for_status()
            return await response.json()
