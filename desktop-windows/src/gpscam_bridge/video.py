from __future__ import annotations

from dataclasses import dataclass
import io
import shutil
import subprocess
import threading
from typing import Optional

import numpy as np
from PIL import Image

try:
    import pyvirtualcam
except Exception:  # pragma: no cover - runtime optional
    pyvirtualcam = None


@dataclass(slots=True)
class VideoState:
    status: str
    detail: str


class VideoReceiver:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._virtual_enabled = False
        self._virtual_status = "disabled"
        self._virtual_cam: Optional[object] = None
        self._last_virtual_error = ""
        self._attempted_backend_install = False

    async def start(self) -> VideoState:
        return VideoState(status="ready", detail="Camera frame receiver ready")

    async def stop(self) -> None:
        with self._lock:
            self._close_virtual_cam_locked()

    def set_virtual_camera_enabled(self, enabled: bool) -> tuple[bool, str]:
        with self._lock:
            if not enabled:
                self._virtual_enabled = False
                self._virtual_status = "disabled"
                self._close_virtual_cam_locked()
                return True, self._virtual_status

            self._virtual_enabled = True
            if pyvirtualcam is None:
                installed, detail = self._try_silent_backend_install_locked()
                if not installed:
                    self._virtual_status = f"backend_missing ({detail})"
                    return False, self._virtual_status
                # Installation happened, but current process still has no module/backend.
                self._virtual_status = "backend_installed_restart_required"
                return False, self._virtual_status

            self._virtual_status = "enabled_waiting_frames"
            return True, self._virtual_status

    def virtual_status(self) -> str:
        with self._lock:
            return self._virtual_status

    def process_frame(self, frame_jpeg: bytes) -> None:
        if not frame_jpeg:
            return

        with Image.open(io.BytesIO(frame_jpeg)) as img:
            rgb = img.convert("RGB")
            arr = np.asarray(rgb, dtype=np.uint8)

        with self._lock:
            if not self._virtual_enabled:
                return
            self._ensure_virtual_cam_locked(width=arr.shape[1], height=arr.shape[0])
            if self._virtual_cam is None:
                return

            try:
                self._virtual_cam.send(arr)
                self._virtual_cam.sleep_until_next_frame()
                self._virtual_status = "streaming"
            except Exception as exc:  # pragma: no cover - depends on host backend
                self._last_virtual_error = str(exc)
                self._virtual_status = f"stream_error ({type(exc).__name__})"
                self._close_virtual_cam_locked()

    def _ensure_virtual_cam_locked(self, width: int, height: int) -> None:
        if self._virtual_cam is not None:
            return
        if pyvirtualcam is None:
            return
        try:
            self._virtual_cam = pyvirtualcam.Camera(width=width, height=height, fps=20, print_fps=False)
            self._virtual_status = f"ready {width}x{height}"
        except Exception as exc:  # pragma: no cover - backend-specific
            self._last_virtual_error = str(exc)
            if not self._attempted_backend_install:
                self._attempted_backend_install = True
                installed, detail = self._try_silent_backend_install_locked()
                if installed:
                    self._virtual_status = "backend_installed_restart_required"
                else:
                    self._virtual_status = f"backend_error ({detail})"
            else:
                self._virtual_status = f"backend_error ({type(exc).__name__})"
            self._virtual_cam = None

    def _close_virtual_cam_locked(self) -> None:
        if self._virtual_cam is None:
            return
        try:
            self._virtual_cam.close()
        except Exception:
            pass
        self._virtual_cam = None

    def _try_silent_backend_install_locked(self) -> tuple[bool, str]:
        # Silent attempt; no interactive prompts from this app.
        if shutil.which("winget"):
            command = [
                "winget",
                "install",
                "-e",
                "--id",
                "OBSProject.OBSStudio",
                "--silent",
                "--accept-package-agreements",
                "--accept-source-agreements",
                "--disable-interactivity",
            ]
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=900)
                if result.returncode == 0:
                    return True, "obs_installed"
                stderr = (result.stderr or "").strip()
                return False, stderr or f"winget_exit_{result.returncode}"
            except Exception as exc:
                return False, f"winget_error:{type(exc).__name__}"

        if shutil.which("choco"):
            command = ["choco", "install", "obs-studio", "-y", "--no-progress"]
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=900)
                if result.returncode == 0:
                    return True, "obs_installed"
                stderr = (result.stderr or "").strip()
                return False, stderr or f"choco_exit_{result.returncode}"
            except Exception as exc:
                return False, f"choco_error:{type(exc).__name__}"

        return False, "no_package_manager"
