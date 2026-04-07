from __future__ import annotations

import asyncio
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from .constants import APP_NAME, APP_VERSION, DEFAULT_PORT, HEALTH_CHECK_INTERVAL_SECONDS
from .discovery import discover_server_on_local_subnets
from .firewall_helper import (
    apply_firewall_rule,
    firewall_commands_for_copy,
    get_firewall_guidance,
    open_firewall_settings,
    open_repo_or_release,
)
from .models import Endpoint, GpsSample, ServerStatus
from .network_client import MobileServerClient
from .recovery import EndpointRecovery
from .video import VideoReceiver


class DesktopBridgeApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} Desktop")
        self.root.geometry("810x450")

        self.events: queue.Queue[dict] = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None

        self.host_var = tk.StringVar(value="")
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        self.status_var = tk.StringVar(value="Disconnected")
        self.endpoint_var = tk.StringVar(value="-")
        self.server_var = tk.StringVar(value="-")
        self.camera_var = tk.StringVar(value="unknown")
        self.gps_var = tk.StringVar(value="No sample")
        self.log_var = tk.StringVar(value="Ready")

        self.repo_url = "https://github.com/aomendes/gpscam-bridge"
        self.release_url = f"{self.repo_url}/releases/latest"

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        top = ttk.LabelFrame(frame, text="Connection")
        top.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(top, text="Mobile IP").grid(row=0, column=0, padx=8, pady=8, sticky=tk.W)
        ttk.Entry(top, textvariable=self.host_var, width=20).grid(row=0, column=1, padx=8, pady=8, sticky=tk.W)

        ttk.Label(top, text="Port").grid(row=0, column=2, padx=8, pady=8, sticky=tk.W)
        ttk.Entry(top, textvariable=self.port_var, width=8).grid(row=0, column=3, padx=8, pady=8, sticky=tk.W)

        self.detect_btn = ttk.Button(top, text="Auto Detect", command=self.auto_detect_and_connect)
        self.detect_btn.grid(row=0, column=4, padx=8, pady=8)

        self.connect_btn = ttk.Button(top, text="Connect", command=self.start_connection)
        self.connect_btn.grid(row=0, column=5, padx=8, pady=8)

        self.disconnect_btn = ttk.Button(top, text="Disconnect", command=self.stop_connection, state=tk.DISABLED)
        self.disconnect_btn.grid(row=0, column=6, padx=8, pady=8)

        status = ttk.LabelFrame(frame, text="Status")
        status.pack(fill=tk.X, pady=(0, 12))

        rows = [
            ("State", self.status_var),
            ("Endpoint", self.endpoint_var),
            ("Server ID", self.server_var),
            ("Camera", self.camera_var),
            ("GPS", self.gps_var),
            ("Log", self.log_var),
        ]

        for idx, (label, var) in enumerate(rows):
            ttk.Label(status, text=f"{label}:", width=10).grid(row=idx, column=0, padx=8, pady=3, sticky=tk.W)
            ttk.Label(status, textvariable=var).grid(row=idx, column=1, padx=8, pady=3, sticky=tk.W)

        actions = ttk.LabelFrame(frame, text="Guided Actions")
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="Apply Firewall Rule", command=self.apply_firewall_rule_clicked).pack(
            side=tk.LEFT, padx=8, pady=8
        )
        ttk.Button(actions, text="Copy Firewall Cmd", command=self.copy_firewall_command_clicked).pack(
            side=tk.LEFT, padx=8, pady=8
        )
        ttk.Button(actions, text="Open Firewall Settings", command=open_firewall_settings).pack(side=tk.LEFT, padx=8, pady=8)
        ttk.Button(actions, text="GitHub Release", command=lambda: open_repo_or_release(self.release_url)).pack(
            side=tk.LEFT, padx=8, pady=8
        )
        ttk.Button(actions, text="Repository", command=lambda: open_repo_or_release(self.repo_url)).pack(
            side=tk.LEFT, padx=8, pady=8
        )

        footer = ttk.Label(frame, text=f"{APP_NAME} v{APP_VERSION}")
        footer.pack(anchor=tk.E, pady=(8, 0))

    def start_connection(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            return

        host = self.host_var.get().strip()

        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            messagebox.showerror(APP_NAME, "Porta invalida.")
            return

        self.stop_event.clear()
        self.detect_btn.config(state=tk.DISABLED)
        self.connect_btn.config(state=tk.DISABLED)
        self.disconnect_btn.config(state=tk.NORMAL)
        self.status_var.set("Connecting")
        self.log_var.set("Auto-detecting mobile server..." if not host else "Starting connection supervisor")

        self.worker_thread = threading.Thread(target=self._run_worker, args=(host, port), daemon=True)
        self.worker_thread.start()
        self._drain_events()

    def auto_detect_and_connect(self) -> None:
        self.host_var.set("")
        self.start_connection()

    def stop_connection(self) -> None:
        self.stop_event.set()
        self.status_var.set("Disconnecting")
        self.log_var.set("Stopping...")

    def apply_firewall_rule_clicked(self) -> None:
        ok, detail = apply_firewall_rule()
        if ok:
            messagebox.showinfo(APP_NAME, f"Firewall: {detail}")
        else:
            self._copy_to_clipboard(firewall_commands_for_copy())
            messagebox.showwarning(
                APP_NAME,
                "Falha ao aplicar regra automaticamente.\n"
                "O comando completo foi copiado para a area de transferencia.\n"
                "Abra PowerShell como administrador e cole para executar.\n\n"
                f"Detalhe: {detail}",
            )

    def copy_firewall_command_clicked(self) -> None:
        self._copy_to_clipboard(firewall_commands_for_copy())
        messagebox.showinfo(APP_NAME, "Comando de firewall copiado. Cole no PowerShell (Admin).")

    def _copy_to_clipboard(self, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()

    def _drain_events(self) -> None:
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            self._apply_event(event)

        alive = self.worker_thread is not None and self.worker_thread.is_alive()
        if alive:
            self.root.after(200, self._drain_events)
        else:
            self.detect_btn.config(state=tk.NORMAL)
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            if self.stop_event.is_set():
                self.status_var.set("Disconnected")

    def _apply_event(self, event: dict) -> None:
        kind = event.get("kind")
        if kind == "log":
            self.log_var.set(event["message"])
            return

        if kind == "connected":
            status: ServerStatus = event["status"]
            endpoint: Endpoint = event["endpoint"]
            self.status_var.set("Connected")
            self.host_var.set(endpoint.host)
            self.port_var.set(str(endpoint.port))
            self.endpoint_var.set(f"{endpoint.host}:{endpoint.port}")
            self.server_var.set(status.server_id)
            self.camera_var.set(status.camera_state)
            self.log_var.set("Stream active")
            return

        if kind == "autodetected":
            endpoint: Endpoint = event["endpoint"]
            self.host_var.set(endpoint.host)
            self.port_var.set(str(endpoint.port))
            self.log_var.set(f"Auto-detected {endpoint.host}:{endpoint.port}")
            return

        if kind == "gps":
            sample: GpsSample = event["sample"]
            self.gps_var.set(
                f"lat={sample.latitude:.6f}, lon={sample.longitude:.6f}, acc={sample.accuracy_m:.1f}m"
            )
            return

        if kind == "disconnected":
            self.status_var.set("Disconnected")
            self.log_var.set(event["message"])
            return

        if kind == "firewall":
            self.status_var.set("Needs attention")
            self.log_var.set("Connection failed after auto-recovery")
            messagebox.showwarning(APP_NAME, get_firewall_guidance())

    def _post(self, event: dict) -> None:
        self.events.put(event)

    def _run_worker(self, host: str, port: int) -> None:
        asyncio.run(self._worker_loop(host, port))

    async def _worker_loop(self, host: str, port: int) -> None:
        client = MobileServerClient()
        recovery = EndpointRecovery(client=client, log=lambda m: self._post({"kind": "log", "message": m}))
        video = VideoReceiver()

        try:
            endpoint, status = await self._resolve_initial_endpoint(client=client, recovery=recovery, host=host, port=port)
            if endpoint is None or status is None:
                self._post({"kind": "firewall"})
                self._post({"kind": "disconnected", "message": "Unable to find mobile server"})
                return

            expected_server_id: Optional[str] = status.server_id

            while not self.stop_event.is_set():
                self._post({"kind": "connected", "status": status, "endpoint": endpoint})

                video_state = await video.start()
                self._post({"kind": "log", "message": video_state.detail})

                disconnected = await self._run_online_loop(client, endpoint)
                await video.stop()
                if not disconnected or self.stop_event.is_set():
                    break

                self._post({"kind": "log", "message": "Connection lost. Starting silent recovery..."})
                recovered_endpoint, recovered_status = await recovery.recover(
                    initial_endpoint=endpoint,
                    expected_server_id=expected_server_id,
                )

                if recovered_endpoint is None or recovered_status is None:
                    recovered_endpoint, recovered_status = await discover_server_on_local_subnets(
                        client=client,
                        preferred_port=endpoint.port,
                        log=lambda m: self._post({"kind": "log", "message": m}),
                    )
                    if recovered_endpoint is None or recovered_status is None:
                        self._post({"kind": "firewall"})
                        self._post({"kind": "disconnected", "message": "Auto-recovery timeout"})
                        return

                endpoint = recovered_endpoint
                self._post({"kind": "autodetected", "endpoint": endpoint})
                self._post({"kind": "connected", "status": recovered_status, "endpoint": endpoint})
                status = recovered_status

        except Exception as exc:
            self._post({"kind": "disconnected", "message": f"Fatal error: {exc}"})
        finally:
            await client.close()
            self._post({"kind": "disconnected", "message": "Connection stopped"})

    async def _resolve_initial_endpoint(
        self,
        client: MobileServerClient,
        recovery: EndpointRecovery,
        host: str,
        port: int,
    ) -> tuple[Endpoint, ServerStatus] | tuple[None, None]:
        endpoint: Endpoint | None = Endpoint(host=host, port=port) if host else None

        if endpoint is not None:
            try:
                status = await self._connect_once(client, endpoint)
                return endpoint, status
            except Exception:
                self._post({"kind": "log", "message": "Initial connection failed. Trying silent auto-detect..."})

            recovered_endpoint, recovered_status = await recovery.recover(
                initial_endpoint=endpoint,
                expected_server_id=None,
                timeout_seconds=12,
            )
            if recovered_endpoint is not None and recovered_status is not None:
                self._post({"kind": "autodetected", "endpoint": recovered_endpoint})
                return recovered_endpoint, recovered_status

        discovered_endpoint, discovered_status = await discover_server_on_local_subnets(
            client=client,
            preferred_port=port,
            log=lambda m: self._post({"kind": "log", "message": m}),
        )
        if discovered_endpoint is not None and discovered_status is not None:
            self._post({"kind": "autodetected", "endpoint": discovered_endpoint})
            return discovered_endpoint, discovered_status

        return None, None

    async def _connect_once(self, client: MobileServerClient, endpoint: Endpoint) -> ServerStatus:
        self._post({"kind": "log", "message": f"Connecting to {endpoint.host}:{endpoint.port}"})
        return await client.get_status(endpoint)

    async def _run_online_loop(self, client: MobileServerClient, endpoint: Endpoint) -> bool:
        last_health = time.monotonic()

        async def gps_reader() -> None:
            async for sample in client.gps_stream(endpoint):
                if self.stop_event.is_set():
                    return
                self._post({"kind": "gps", "sample": sample})

        async def health_reader() -> None:
            nonlocal last_health
            while not self.stop_event.is_set():
                ok = await client.check_health(endpoint)
                if not ok:
                    raise RuntimeError("Health check failed")
                last_health = time.monotonic()
                await asyncio.sleep(HEALTH_CHECK_INTERVAL_SECONDS)

        gps_task = asyncio.create_task(gps_reader())
        health_task = asyncio.create_task(health_reader())

        while not self.stop_event.is_set():
            done, _ = await asyncio.wait({gps_task, health_task}, timeout=1, return_when=asyncio.FIRST_EXCEPTION)
            if not done:
                if time.monotonic() - last_health > (HEALTH_CHECK_INTERVAL_SECONDS * 3):
                    break
                continue
            for task in done:
                if task.exception() is not None:
                    break
            break

        for task in (gps_task, health_task):
            task.cancel()
        await asyncio.gather(gps_task, health_task, return_exceptions=True)
        return not self.stop_event.is_set()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = DesktopBridgeApp()
    app.run()


if __name__ == "__main__":
    main()
