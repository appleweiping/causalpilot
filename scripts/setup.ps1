param(
    [string]$Python = "py",
    [string[]]$PythonArgs = @("-3.11")
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $RepoRoot ".venv"
$PackageLock = Join-Path $RepoRoot "frontend\package-lock.json"

if (-not (Test-Path -LiteralPath $PackageLock)) {
    throw "Missing frontend\package-lock.json. A reproducible setup requires the checked-in lockfile."
}

if (-not (Test-Path -LiteralPath $VenvPath)) {
    & $Python @PythonArgs -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { throw "Failed to create the Python virtual environment." }
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
& $VenvPython -m pip install -e "$RepoRoot\backend[test]"
if ($LASTEXITCODE -ne 0) { throw "Failed to install backend dependencies." }
& npm.cmd --prefix "$RepoRoot\frontend" ci
if ($LASTEXITCODE -ne 0) { throw "Failed to install frontend dependencies from package-lock.json." }

Write-Host "Setup complete. Run .\scripts\run_demo.ps1"
