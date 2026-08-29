# MiniGit Installation & Deployment Guide

This guide covers how to install and uninstall the standalone **MiniGit CLI** on Windows, Linux, and macOS without needing Python, as well as deploying the **MiniGit Server** to production using **Dokploy**.

---

## 1. Client Installation (No Python Required)

The MiniGit client is distributed as a self-contained executable binary for Windows, Linux, and macOS.

### Automated 1-Line Installation (Recommended)

The automated script automatically downloads the correct binary for your OS and CPU architecture, installs it, and adds it to your system environment `PATH` so you can type `minigit` from any directory.

#### **Linux & macOS**:
```bash
curl -fsSL https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/install.sh | bash
```
> Installed to: `~/.minigit/bin/minigit`  
> Automatically configured in: `~/.bashrc`, `~/.zshrc`, or `~/.profile`.

To use immediately in your current terminal session without reopening it:
```bash
export PATH="$HOME/.minigit/bin:$PATH"
```

#### **Windows (PowerShell)**:
```powershell
irm https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/install.ps1 | iex
```
> Installed to: `%LOCALAPPDATA%\MiniGit\bin\minigit.exe`  
> Automatically configured in: Windows User Environment `PATH`.

---

### Manual Installation Step-by-Step

If you prefer downloading and placing the binary yourself instead of using the script:

1. Go to [GitHub Releases](https://github.com/Anirban-dev/Git/releases) and download the binary matching your system:
   - **Windows**: `minigit-windows-x86_64.exe` $\rightarrow$ Rename to `minigit.exe`
   - **Linux**: `minigit-linux-x86_64` $\rightarrow$ Rename to `minigit`
   - **macOS (Apple Silicon M1/M2/M3)**: `minigit-macos-arm64` $\rightarrow$ Rename to `minigit`
   - **macOS (Intel)**: `minigit-macos-x86_64` $\rightarrow$ Rename to `minigit`

2. Move it to a folder in your system's `PATH`:
   - **Linux / macOS**: Move to `/usr/local/bin` (or `~/.local/bin`) and grant execution permissions:
     ```bash
     sudo mv minigit /usr/local/bin/minigit
     sudo chmod +x /usr/local/bin/minigit
     ```
   - **Windows**: Move `minigit.exe` to `C:\Windows\` or create a folder like `C:\tools\minigit` and add `C:\tools\minigit` to your system Environment Variables under **Path**.

---

## 2. Client Uninstallation (Removing MiniGit)

To completely remove MiniGit, delete its files, and clean it from your `PATH` environment variable:

### Automated 1-Line Uninstallation

#### **Linux & macOS**:
```bash
curl -fsSL https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/uninstall.sh | bash
```

#### **Windows (PowerShell)**:
```powershell
irm https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/uninstall.ps1 | iex
```

### Manual Removal
- **Linux & macOS**:
  ```bash
  rm -rf ~/.minigit
  # Remove the 'export PATH="$HOME/.minigit/bin:$PATH"' line from ~/.bashrc or ~/.zshrc
  ```
- **Windows**:
  - Delete folder: `%LOCALAPPDATA%\MiniGit`
  - Open **Edit the system environment variables** $\rightarrow$ Click **Environment Variables** $\rightarrow$ Select **Path** under User variables $\rightarrow$ Delete the entry for `MiniGit\bin`.

---

## 3. Server Deployment with Dokploy

Deploy the MiniGit server container easily to your Dokploy host.

### Step 1: Connect Repository
1. In Dokploy, click **Create Application**.
2. Select **GitHub** as the source and choose repository: `Anirban-dev/Git`.
3. Set **Branch**: `main`.
4. Set **Build Type**: `Dockerfile` (using `Dockerfile`).

### Step 2: Configure Environment Variables
In the Dokploy **Environment** tab, set:
```env
MINIGIT_SECRET_KEY=generate-a-strong-random-secret-key
MINIGIT_SERVER_PORT=3000
EMAIL_USER=your-email@gmail.com
EMAIL_PASS=your-gmail-app-password
```

### Step 3: Persistent Volume Mount
To ensure repository files and user data persist across container restarts/redeploys:
- **Host Path / Volume**: `minigit_storage` (or `/var/lib/minigit/storage`)
- **Mount Path**: `/app/storage`

### Step 4: Deploy & Domain Setup
1. Expose port `3000` or map your custom domain (e.g. `git.yourdomain.com`).
2. Click **Deploy**.

---

## 4. Verifying Installation & Getting Started

1. Check that the CLI is accessible:
   ```bash
   minigit help
   ```

2. Register an account against your deployed server:
   ```bash
   minigit auth register --server https://git.yourdomain.com
   ```

3. Initialize a repository, commit, and push:
   ```bash
   minigit init my-repo
   cd my-repo
   echo "# Hello MiniGit" > README.md
   minigit add .
   minigit commit -m "Initial commit"
   minigit remote add origin https://git.yourdomain.com/repos/username/my-repo --create
   minigit push origin main
   ```
