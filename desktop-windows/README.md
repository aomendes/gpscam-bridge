# GpsCam Bridge Desktop (Windows)

Aplicativo desktop para conectar ao servidor local do celular e consumir:
- `GET /api/status`
- `GET /api/health`
- `WS /api/gps`

Inclui auto-recuperacao:
- reconexao silenciosa;
- fallback de portas `8765-8775`;
- varredura da sub-rede `/24` por `server_id`;
- assistente de firewall quando recovery excede 60s.

## Executar em desenvolvimento

```powershell
cd desktop-windows
python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
python -m gpscam_bridge
```

## Gerar .exe

```powershell
cd desktop-windows
.\scripts\build_exe.ps1
```

Para copiar automaticamente o `.exe` para os assets Android:

```powershell
.\scripts\build_exe.ps1 -MobileAssetsPath "..\mobile-android\app\src\main\assets\windows"
```
