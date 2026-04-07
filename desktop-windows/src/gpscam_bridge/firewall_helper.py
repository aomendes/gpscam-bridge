from __future__ import annotations

import subprocess
import webbrowser


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
