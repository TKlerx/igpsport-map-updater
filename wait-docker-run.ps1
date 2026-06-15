param(
    [string]$Container,
    [string]$Image = "igpsport-map-updater",
    [string]$CommandContains = "./run.sh input",
    [int]$PollSeconds = 10
)

$ErrorActionPreference = "Stop"

function Get-MatchingContainers {
    docker ps --filter "ancestor=$Image" --format "{{.ID}}`t{{.Names}}`t{{.Command}}`t{{.Status}}" |
        ForEach-Object {
            $parts = $_ -split "`t", 4
            [pscustomobject]@{
                Id      = $parts[0]
                Name    = $parts[1]
                Command = $parts[2]
                Status  = $parts[3]
            }
        } |
        Where-Object {
            if ($Container) {
                $_.Id.StartsWith($Container) -or $_.Name -eq $Container
            } else {
                $_.Command -like "*$CommandContains*"
            }
        }
}

$matches = @(Get-MatchingContainers)
if ($matches.Count -eq 0) {
    Write-Host "No matching running docker job found."
    exit 0
}

if ($matches.Count -gt 1 -and -not $Container) {
    Write-Host "Multiple matching docker jobs found. Re-run with -Container <id-or-name>."
    $matches | Format-Table -AutoSize
    exit 2
}

$job = $matches[0]
Write-Host "Waiting for docker job $($job.Id) ($($job.Name)): $($job.Command)"

if ($Container) {
    $exitCode = docker wait $job.Id
    Write-Host "Docker job is done: $($job.Id) ($($job.Name)); exit code: $exitCode"
    exit [int]$exitCode
}

while ($true) {
    $stillRunning = @(Get-MatchingContainers | Where-Object { $_.Id -eq $job.Id -or $_.Name -eq $job.Name })
    if ($stillRunning.Count -eq 0) {
        Write-Host "Docker job is done: $($job.Id) ($($job.Name))"
        exit 0
    }

    $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$now] Still running: $($stillRunning[0].Status)"
    Start-Sleep -Seconds $PollSeconds
}
