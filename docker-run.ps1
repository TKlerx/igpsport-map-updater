param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string] $InputDir,

    [switch] $Resume,

    [string] $Image = "igpsport-map-updater"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $InputDir -PathType Container)) {
    throw "Input directory not found: $InputDir"
}

foreach ($dir in @("download", "tmp", "output", "packages")) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$inputFull = (Resolve-Path -LiteralPath $InputDir).Path
$root = (Get-Location).Path
$runArgs = @("./run.sh", "input")
if ($Resume) {
    $runArgs += "--resume"
}

$tagProfile = if ($env:MAP_TAG_PROFILE) { $env:MAP_TAG_PROFILE } else { "enhanced" }
$javaTmp = if ($env:JAVA_TMP_DIR) { $env:JAVA_TMP_DIR } else { "/work/tmp" }

docker run --rm `
    -e "MAP_TAG_PROFILE=$tagProfile" `
    -e "MAP_RESUME=$env:MAP_RESUME" `
    -e "JAVA_TMP_DIR=$javaTmp" `
    -e "JAVA_XMS=$env:JAVA_XMS" `
    -e "JAVA_XMX=$env:JAVA_XMX" `
    -v "${inputFull}:/work/input" `
    -v "${root}/download:/work/download" `
    -v "${root}/tmp:/work/tmp" `
    -v "${root}/output:/work/output" `
    -v "${root}/packages:/work/packages" `
    $Image @runArgs
