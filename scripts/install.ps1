# MiniGit Standalone Client Installer for Windows (PowerShell)
# Usage: irm https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/install.ps1 | iex

$ErrorActionPreference = "Stop"

$Repo = "Anirban-dev/Git"
$InstallDir = "$env:LOCALAPPDATA\MiniGit\bin"
$BinaryName = "minigit-windows-x86_64.exe"
$TargetExe = Join-Path $InstallDir "minigit.exe"

Write-Host "==> Installing MiniGit CLI for Windows..." -ForegroundColor Cyan

# 1. Prepare target directory
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# 2. Download latest binary from GitHub Releases
$DownloadUrl = "https://github.com/$Repo/releases/latest/download/$BinaryName"

Write-Host "==> Downloading from: $DownloadUrl" -ForegroundColor Cyan

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $TargetExe -UseBasicParsing
} catch {
    Write-Host "Direct download failed, querying latest release API..." -ForegroundColor Yellow
    try {
        $ReleaseApi = "https://api.github.com/repos/$Repo/releases/latest"
        $ReleaseJson = Invoke-RestMethod -Uri $ReleaseApi -UseBasicParsing
        $Asset = $ReleaseJson.assets | Where-Object { $_.name -like "*windows*.exe" -or $_.name -like "*minigit*.exe" } | Select-Object -First 1
        if ($Asset) {
            Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $TargetExe -UseBasicParsing
        } else {
            throw "No Windows binary found in latest release assets."
        }
    } catch {
        Write-Host "Error: Failed to download MiniGit binary. Please verify that a release exists at https://github.com/$Repo/releases" -ForegroundColor Red
        Exit 1
    }
}

# 3. Add to User PATH environment variable if not already present
$UserPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
if ($UserPath -notlike "*$InstallDir*") {
    $NewUserPath = "$UserPath;$InstallDir"
    [Environment]::SetEnvironmentVariable("Path", $NewUserPath, [EnvironmentVariableTarget]::User)
    Write-Host "==> Added $InstallDir to User PATH." -ForegroundColor Green
}

# Update current session PATH so minigit works immediately in this window
if ($env:PATH -notlike "*$InstallDir*") {
    $env:PATH = "$env:PATH;$InstallDir"
}

Write-Host ""
Write-Host "✔ MiniGit CLI successfully installed to: $TargetExe" -ForegroundColor Green
Write-Host ""
Write-Host "You can now run:" -ForegroundColor White
Write-Host "  minigit help" -ForegroundColor Cyan
Write-Host "  minigit auth register --server https://<your-dokploy-server-url>" -ForegroundColor Cyan
