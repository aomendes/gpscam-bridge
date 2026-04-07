# Mobile Android

App Android para expor camera+GPS ao desktop na mesma rede.

## Endpoints
- `GET /`
- `GET /download/windows`
- `GET /api/status`
- `GET /api/health`
- `POST /api/webrtc/offer`
- `POST /api/webrtc/ice`
- `WS /api/gps`

## Configurar links GitHub
Edite `ServerConfig.kt` e altere:
- `REPOSITORY_URL`
- `RELEASES_URL`

Quando publicar no GitHub, use o workflow em `.github/workflows/desktop-release.yml` para gerar e anexar o `.exe` no Release.

## Assets Windows
`app/src/main/assets/windows/GpsCamBridgeDesktop.exe` e servido por `/download/windows`.

## Build
Abra a pasta `mobile-android` no Android Studio e sincronize o Gradle.
