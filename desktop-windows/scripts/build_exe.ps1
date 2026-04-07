param(
    [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\.."),
    [string]$MobileAssetsPath = ""
)

$ErrorActionPreference = "Stop"

Push-Location $ProjectRoot
try {
    python -m pip install -r requirements.txt

    pyinstaller --noconfirm --clean --windowed --onefile --name GpsCamBridgeDesktop --paths src src\gpscam_bridge\main.py

    if ($MobileAssetsPath -ne "") {
        New-Item -ItemType Directory -Force -Path $MobileAssetsPath | Out-Null
        Copy-Item -LiteralPath "$ProjectRoot\dist\GpsCamBridgeDesktop.exe" -Destination "$MobileAssetsPath\GpsCamBridgeDesktop.exe" -Force
    }
}
finally {
    Pop-Location
}
