# GpsCam Bridge

Monorepo com duas partes:
- `mobile-android/`: app Android que inicia servidor local Wi-Fi, exibe IP+porta+QR e disponibiliza download do executavel Windows.
- `desktop-windows/`: app Windows (Python/Tkinter) com reconexao automatica, fallback de portas e scan /24.

## Funcionalidades implementadas

### Android
- Porta padrao `8765` com fallback automatico ate `8775`.
- UI com:
  - IP/porta atual,
  - `server_id`,
  - estado de camera e GPS,
  - QR code dinamico.
- `GET /`: pagina HTML de instalacao com:
  - botao para `GET /download/windows`,
  - link para GitHub Releases,
  - link para repositorio.
- `GET /api/status`, `GET /api/health`.
- `WS /api/gps` com stream JSON.
- `POST /api/webrtc/offer` e `POST /api/webrtc/ice` (sinalizacao pronta para evolucao do receiver completo).

### Windows
- App desktop com entrada de IP/porta.
- Conexao principal via `GET /api/status`.
- Auto-correcao silenciosa:
  - reconexao imediata,
  - backoff `1,2,5,10,15` (loop),
  - fallback de portas `8765-8775`,
  - scan de sub-rede `/24` por `server_id`.
- Retoma GPS automaticamente apos recuperar conexao.
- Diagnostico guiado de firewall com botao para abrir configuracoes.
- Build de `.exe` com PyInstaller.

## Estrutura

```text
mobile-android/
desktop-windows/
```

## Build do executavel Windows

```powershell
cd desktop-windows
.\scripts\build_exe.ps1
```

Para copiar diretamente para os assets Android:

```powershell
.\scripts\build_exe.ps1 -MobileAssetsPath "..\mobile-android\app\src\main\assets\windows"
```

## Repositorio Git e Releases

1. Inicialize o repositorio local:

```powershell
git init
git branch -M main
git add .
git commit -m "feat: initial gpscam bridge implementation"
```

2. Crie repositorio remoto no GitHub e conecte:

```powershell
git remote add origin https://github.com/<seu-usuario>/gpscam-bridge.git
git push -u origin main
```

3. Gere release com o `.exe` automaticamente:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

O workflow `.github/workflows/desktop-release.yml` publica `GpsCamBridgeDesktop.exe` no GitHub Releases.

## Observacoes importantes

- Atualize em `mobile-android/app/src/main/java/com/gpscambridge/mobile/network/ServerConfig.kt`:
  - `REPOSITORY_URL`
  - `RELEASES_URL`
- O arquivo `GpsCamBridgeDesktop.exe` ja foi copiado em `mobile-android/app/src/main/assets/windows/`.
- Neste ambiente nao ha SDK .NET instalado e nao ha Gradle global; o app Windows foi entregue em Python+exe e o app Android foi estruturado para abrir no Android Studio/Gradle Wrapper.
