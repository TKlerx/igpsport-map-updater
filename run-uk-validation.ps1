param(
    [ValidateSet("baseline", "preclip")]
    [string]$Mode = "baseline",
    [switch]$Detached,
    [string]$Name
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$outputName = if ($Mode -eq "baseline") { "output-uk-baseline" } else { "output-uk-preclip" }
$preclipMode = if ($Mode -eq "baseline") { "disabled" } else { "auto" }
$containerName = if ($Name) { $Name } else { "igpsport-uk-$Mode" }

New-Item -ItemType Directory -Force -Path `
    (Join-Path $repo "input-uk"), `
    (Join-Path $repo "download"), `
    (Join-Path $repo "tmp"), `
    (Join-Path $repo $outputName), `
    (Join-Path $repo "validation-packages"), `
    (Join-Path $repo "logs") | Out-Null

$dockerArgs = @(
    "run", "--rm",
    "--name", $containerName,
    "-e", "MAP_PRECLIP_MODE=$preclipMode",
    "-e", "MAP_RESUME=1",
    "-v", "$repo\input-uk:/work/input:ro",
    "-v", "$repo\download:/work/download",
    "-v", "$repo\tmp:/work/tmp",
    "-v", "$repo\$outputName:/work/output",
    "-v", "$repo\validation-packages:/work/packages",
    "igpsport-map-updater",
    "./run.sh", "input", "--resume"
)

if ($Detached) {
    $logPath = Join-Path $repo "logs\$containerName.log"
    $id = docker @dockerArgs -d
    Write-Host "Started $containerName ($id)"
    Write-Host "Log: $logPath"
    Start-Process -WindowStyle Hidden -FilePath "powershell" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        "docker logs -f $containerName *> '$logPath'"
    ) | Out-Null
    exit 0
}

docker @dockerArgs
