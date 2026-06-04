param(
    [Parameter(Position = 0)]
    [string]$MapsDir,
    [switch]$Resume
)

$ErrorActionPreference = "Stop"

$SCRIPT_DIR = $PSScriptRoot
$PYTHON = if ([string]::IsNullOrWhiteSpace($env:PYTHON)) { "python" } else { $env:PYTHON }

# Check for original maps directory argument
if ([string]::IsNullOrWhiteSpace($MapsDir)) {
    Write-Host "Usage: .\run.ps1 <directory_with_original_maps> [-Resume]"
    Write-Host ""
    Write-Host "Example:"
    Write-Host "  .\run.ps1 backup\"
    Write-Host "  .\run.ps1 'C:\Users\me\igpsport-maps\original'"
    Write-Host "  .\run.ps1 input -Resume"
    exit 1
}

$MAPS_DIR = $MapsDir

if (-not (Test-Path $MAPS_DIR -PathType Container)) {
    Write-Error "Error: '$MAPS_DIR' is not a directory."
    exit 1
}

# Step 1: Generate maps.csv
Write-Host ""
Write-Host "=========================================="
Write-Host "Step 1: Generating maps.csv"
Write-Host "=========================================="
Write-Host ""

& $PYTHON (Join-Path $SCRIPT_DIR "generate_maps_csv.py") $MAPS_DIR -o (Join-Path $SCRIPT_DIR "maps.csv")

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to generate maps.csv"
    exit 1
}

# Step 2: Generate maps
Write-Host ""
Write-Host "=========================================="
Write-Host "Step 2: Generating maps"
Write-Host "=========================================="
Write-Host ""

if ($Resume) {
    $env:MAP_RESUME = "1"
    Write-Host "Resume mode enabled: existing output maps for the same country/product/date will be skipped."
    Write-Host ""
}

$env:MAP_INPUT_DIR = (Resolve-Path $MAPS_DIR).Path
& (Join-Path $SCRIPT_DIR "script.ps1")
