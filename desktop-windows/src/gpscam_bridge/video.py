from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class VideoState:
    status: str
    detail: str


class VideoReceiver:
    """Minimal placeholder for WebRTC integration on desktop.

    The signaling contract is implemented in network_client; this class is kept
    so phase-2 can drop in aiortc without changing UI/control flow.
    """

    async def start(self) -> VideoState:
        return VideoState(status="pending", detail="WebRTC receiver scaffold ready")

    async def stop(self) -> None:
        return None
