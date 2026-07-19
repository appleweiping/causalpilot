param(
    [ValidateRange(1024, 65535)]
    [int]$ApiPort = 8000,
    [ValidateRange(1024, 65535)]
    [int]$WebPort = 3000
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$LogDir = Join-Path $RepoRoot ".cache\logs"

if ($ApiPort -eq $WebPort) {
    throw "ApiPort and WebPort must be different."
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "Missing .venv. Run .\scripts\setup.ps1 first."
}
if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot "frontend\node_modules"))) {
    throw "Missing frontend dependencies. Run .\scripts\setup.ps1 first."
}

$null = New-Item -ItemType Directory -Path $LogDir -Force
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ApiOut = Join-Path $LogDir "api-$Stamp.out.log"
$ApiErr = Join-Path $LogDir "api-$Stamp.err.log"
$WebOut = Join-Path $LogDir "web-$Stamp.out.log"
$WebErr = Join-Path $LogDir "web-$Stamp.err.log"
$ApiArgs = @("-m", "uvicorn", "causalpilot.main:app", "--host", "127.0.0.1", "--port", "$ApiPort")
$Api = $null
$Web = $null

function Wait-ForService {
    param(
        [string]$Name,
        [string]$Uri,
        [System.Diagnostics.Process]$Process,
        [string]$ErrorLog
    )

    for ($Attempt = 1; $Attempt -le 60; $Attempt++) {
        $Process.Refresh()
        if ($Process.HasExited) {
            $Tail = if (Test-Path -LiteralPath $ErrorLog) {
                (Get-Content -LiteralPath $ErrorLog -Tail 20) -join [Environment]::NewLine
            } else { "No error log was written." }
            throw "$Name exited during startup with code $($Process.ExitCode).`n$Tail"
        }
        try {
            $null = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 1
            return
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }
    throw "$Name did not become ready at $Uri within 60 seconds. See $ErrorLog"
}

try {
    $Api = Start-Process -FilePath $VenvPython -ArgumentList $ApiArgs -WorkingDirectory (Join-Path $RepoRoot "backend") -RedirectStandardOutput $ApiOut -RedirectStandardError $ApiErr -PassThru -WindowStyle Hidden
    $Web = Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "dev", "--", "-p", "$WebPort") -WorkingDirectory (Join-Path $RepoRoot "frontend") -RedirectStandardOutput $WebOut -RedirectStandardError $WebErr -PassThru -WindowStyle Hidden

    Wait-ForService -Name "API" -Uri "http://127.0.0.1:$ApiPort/health" -Process $Api -ErrorLog $ApiErr
    Wait-ForService -Name "Web app" -Uri "http://127.0.0.1:$WebPort" -Process $Web -ErrorLog $WebErr

    Write-Host "CausalPilot API: http://127.0.0.1:$ApiPort/docs"
    Write-Host "Control room:   http://127.0.0.1:$WebPort"
    Write-Host "Service logs:   $LogDir"
    Write-Host "Press Ctrl+C to stop both services."
    while (-not $Api.HasExited -and -not $Web.HasExited) {
        Start-Sleep -Seconds 1
        $Api.Refresh()
        $Web.Refresh()
    }
    if ($Api.HasExited) { throw "API exited with code $($Api.ExitCode)." }
    if ($Web.HasExited) { throw "Web app exited with code $($Web.ExitCode)." }
}
finally {
    if ($null -ne $Api -and -not $Api.HasExited) { Stop-Process -Id $Api.Id -Force }
    if ($null -ne $Web -and -not $Web.HasExited) { Stop-Process -Id $Web.Id -Force }
}
