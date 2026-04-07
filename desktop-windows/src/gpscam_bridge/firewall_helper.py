from __future__ import annotations

import sys
import subprocess
import webbrowser
from pathlib import Path


def get_firewall_guidance() -> str:
    return (
        "Nao foi possivel restabelecer conexao automaticamente.\n"
        "1) Verifique se celular e PC estao na mesma rede Wi-Fi.\n"
        "2) Permita o app no Firewall do Windows para rede privada.\n"
        "3) Confirme se o app Android ainda mostra o servidor ativo e a porta correta."
    )


def open_firewall_settings() -> None:
    commands = [
        ["control.exe", "/name", "Microsoft.WindowsFirewall"],
        ["powershell", "-NoProfile", "-Command", "Start-Process 'ms-settings:windowsdefender'"]
    ]

    for cmd in commands:
        try:
            subprocess.Popen(cmd)
            return
        except OSError:
            continue


def open_repo_or_release(url: str) -> None:
    webbrowser.open(url)


def firewall_command_preview() -> str:
    return (
        "netsh advfirewall firewall add rule "
        "name=\"GpsCam Bridge TCP In\" dir=in action=allow protocol=TCP localport=8765-8775 profile=private"
    )


def apply_firewall_rule() -> tuple[bool, str]:
    exe_path = str(Path(sys.executable).resolve())

    commands = [
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            "name=GpsCam Bridge TCP In",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            "localport=8765-8775",
            "profile=private",
        ],
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            "name=GpsCam Bridge TCP Out",
            "dir=out",
            "action=allow",
            "protocol=TCP",
            "remoteport=8765-8775",
            "profile=private",
        ],
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            "name=GpsCam Bridge Program In",
            "dir=in",
            "action=allow",
            f"program={exe_path}",
            "enable=yes",
            "profile=private",
        ],
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            "name=GpsCam Bridge Program Out",
            "dir=out",
            "action=allow",
            f"program={exe_path}",
            "enable=yes",
            "profile=private",
        ],
    ]

    outputs: list[str] = []
    for cmd in commands:
        result = subprocess.run(cmd, capture_output=True, text=True)
        combined = "\n".join([result.stdout.strip(), result.stderr.strip()]).strip()
        outputs.append(combined)
        if result.returncode != 0:
            return False, combined or "Failed to add firewall rule."

    return True, "\n".join(outputs).strip() or "Firewall rules applied."
