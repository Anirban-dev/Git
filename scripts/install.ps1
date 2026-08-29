# MiniGit Standalone Client Installer for Windows (PowerShell)
# Usage: irm https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/install.ps1 | iex

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

$DownloadSuccess = $false

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $TargetExe -UseBasicParsing -ErrorAction Stop
    $DownloadSuccess = $true
} catch {
    Write-Host "Direct download failed, querying latest GitHub release assets..." -ForegroundColor Yellow
    try {
        $ReleaseApi = "https://api.github.com/repos/$Repo/releases/latest"
        $ReleaseJson = Invoke-RestMethod -Uri $ReleaseApi -UseBasicParsing -ErrorAction Stop
        $Asset = $ReleaseJson.assets | Where-Object { $_.name -like "*windows*.exe" -or $_.name -like "*minigit*.exe" } | Select-Object -First 1
        if ($Asset) {
            Write-Host "Found asset: $($Asset.name). Downloading..." -ForegroundColor Cyan
            Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $TargetExe -UseBasicParsing -ErrorAction Stop
            $DownloadSuccess = $true
        } else {
            Write-Host "No Windows binary found in the latest release assets." -ForegroundColor Red
        }
    } catch {
        Write-Host "Error: No release found yet on https://github.com/$Repo/releases" -ForegroundColor Red
    }
}

if (-not $DownloadSuccess) {
    Write-Host ""
    Write-Host "==========================================================================" -ForegroundColor Red
    Write-Host " MiniGit binary could not be downloaded." -ForegroundColor Red
    Write-Host " Please make sure GitHub Actions has finished building the release assets" -ForegroundColor Yellow
    Write-Host " at: https://github.com/$Repo/actions" -ForegroundColor Yellow
    Write-Host "==========================================================================" -ForegroundColor Red
    return
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
