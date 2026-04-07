from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class ServerStatus:
    app_version: str
    server_id: str
    ip: str
    port: int
    camera_state: str
    gps_state: str


@dataclass(slots=True)
class Endpoint:
    host: str
    port: int

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass(slots=True)
class GpsSample:
    latitude: float
    longitude: float
    accuracy_m: float
    heading_deg: Optional[float]
    speed_mps: Optional[float]
    timestamp_ms: int
