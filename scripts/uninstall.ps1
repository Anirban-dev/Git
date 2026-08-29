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

# 2. Remove from Windows Registry User PATH and broadcast change
try {
    $RegKey = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey("Environment", $true)
    $CurrentRawPath = $RegKey.GetValue("Path", "", [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
    if ($CurrentRawPath) {
        $PathParts = $CurrentRawPath -split ";" | Where-Object { $_ -and $_ -ne $BinDir -and $_ -ne "$InstallDir\bin" }
        $NewRawPath = ($PathParts -join ";").Trim(";")
        $RegKey.SetValue("Path", $NewRawPath, [Microsoft.Win32.RegistryValueKind]::ExpandString)
    }
    $RegKey.Close()
} catch {}

[Environment]::SetEnvironmentVariable("Path", $NewRawPath, [EnvironmentVariableTarget]::User)

# 3. Broadcast setting change
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

# Clean up current session PATH
$SessionPathEntries = $env:PATH -split ";" | Where-Object { $_ -ne $BinDir -and $_ -ne "" }
$env:PATH = $SessionPathEntries -join ";"

Write-Host ""
Write-Host "✔ MiniGit CLI has been completely uninstalled." -ForegroundColor Green
Write-Host "Please restart any open terminal windows." -ForegroundColor White
