# MiniGit Standalone Client Uninstaller for Windows (PowerShell)
# Usage: irm https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/uninstall.ps1 | iex

$ErrorActionPreference = "Stop"

$InstallDir = "$env:LOCALAPPDATA\MiniGit"
$BinDir = "$env:LOCALAPPDATA\MiniGit\bin"

Write-Host "==> Uninstalling MiniGit CLI for Windows..." -ForegroundColor Cyan

# 1. Remove files & directory
if (Test-Path $InstallDir) {
    Remove-Item -Path $InstallDir -Recurse -Force | Out-Null
    Write-Host "✔ Removed files from $InstallDir" -ForegroundColor Green
} else {
    Write-Host "MiniGit directory not found at $InstallDir." -ForegroundColor Yellow
}

# 2. Remove from User PATH environment variable
$UserPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
if ($UserPath -like "*$BinDir*") {
    $PathEntries = $UserPath -split ";" | Where-Object { $_ -ne $BinDir -and $_ -ne "" }
    $NewUserPath = $PathEntries -join ";"
    [Environment]::SetEnvironmentVariable("Path", $NewUserPath, [EnvironmentVariableTarget]::User)
    Write-Host "✔ Removed $BinDir from User PATH." -ForegroundColor Green
}

# 3. Clean up current session PATH
$SessionPathEntries = $env:PATH -split ";" | Where-Object { $_ -ne $BinDir -and $_ -ne "" }
$env:PATH = $SessionPathEntries -join ";"

Write-Host ""
Write-Host "✔ MiniGit CLI has been completely uninstalled." -ForegroundColor Green
Write-Host "Please restart any open terminal windows." -ForegroundColor White
