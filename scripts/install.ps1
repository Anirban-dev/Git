# MiniGit Standalone Client Installer for Windows (PowerShell)
# Usage: irm https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/install.ps1 | iex

$Repo = "Anirban-dev/Git"
$InstallDir = "$env:LOCALAPPDATA\MiniGit\bin"
$BinaryName = "minigit-windows-x86_64.exe"
$TargetExe = Join-Path $InstallDir "minigit.exe"
$TargetCmd = Join-Path $InstallDir "minigit.cmd"

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

# 3. Create wrapper batch/cmd script
Set-Content -Path $TargetCmd -Value "@echo off`r`n`"%~dp0minigit.exe`" %*" -Force

# 4. Permanently update Windows Registry for User PATH and broadcast environment change
$RegKey = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey("Environment", $true)
$CurrentRawPath = $RegKey.GetValue("Path", "", [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)

# Split and filter out existing occurrences of InstallDir
$PathParts = $CurrentRawPath -split ";" | Where-Object { $_ -and $_ -ne $InstallDir }
# Prepend InstallDir to the front
$NewRawPath = ($InstallDir, $PathParts -join ";").Trim(";")

# Save back to registry as ExpandString
$RegKey.SetValue("Path", $NewRawPath, [Microsoft.Win32.RegistryValueKind]::ExpandString)
$RegKey.Close()

# Also set via .NET Environment as fallback
[Environment]::SetEnvironmentVariable("Path", $NewRawPath, [EnvironmentVariableTarget]::User)

# 5. Broadcast WM_SETTINGCHANGE message so Windows Explorer and newly spawned shells immediately see the new PATH
try {
    Add-Type -Namespace Win32 -Name NativeMethods -MemberDefinition @"
[System.Runtime.InteropServices.DllImport("user32.dll", SetLastError = true, CharSet = System.Runtime.InteropServices.CharSet.Auto)]
public static extern System.IntPtr SendMessageTimeout(
    System.IntPtr hWnd,
    uint Msg,
    System.UIntPtr wParam,
    string lParam,
    uint fuFlags,
    uint uTimeout,
    out System.UIntPtr lpdwResult);
"@
    $HWND_BROADCAST = [System.IntPtr]0xffff
    $WM_SETTINGCHANGE = 0x001A
    $SMTO_ABORTIFHUNG = 0x0002
    $result = [System.UIntPtr]::Zero
    [Win32.NativeMethods]::SendMessageTimeout($HWND_BROADCAST, $WM_SETTINGCHANGE, [System.UIntPtr]::Zero, "Environment", $SMTO_ABORTIFHUNG, 3000, [ref]$result) | Out-Null
} catch {}

# Update current session PATH so it works immediately in the current window too
if ($env:PATH -notlike "*$InstallDir*") {
    $env:PATH = "$InstallDir;$env:PATH"
}

Write-Host ""
Write-Host "✔ MiniGit CLI successfully installed to: $TargetExe" -ForegroundColor Green
Write-Host "✔ PATH environment variable updated permanently in Windows Registry." -ForegroundColor Green
Write-Host ""
Write-Host "You can now run:" -ForegroundColor White
Write-Host "  minigit help" -ForegroundColor Cyan
Write-Host "  minigit auth login" -ForegroundColor Cyan
Write-Host "  minigit auth register --server $env:MINIGIT_SERVER_URL" -ForegroundColor Cyan
