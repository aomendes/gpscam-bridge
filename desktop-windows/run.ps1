$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "$PSScriptRoot\src"
python -m gpscam_bridge
