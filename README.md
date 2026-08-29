# MiniGit (v2.0)

> A lightweight, multi-account, decentralized Version Control System with custom object storage, SHA-256 tree hashing, OTP-verified user authentication, and a zero-dependency standalone CLI for **Windows**, **macOS**, and **Linux**.

[![Release](https://img.shields.io/github/v/release/Anirban-dev/Git?color=blue&label=Latest%20Release)](https://github.com/Anirban-dev/Git/releases)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ Features

- **Standalone Executable CLI**: Download and run `minigit` on Windows, Linux, and macOS without needing Python or external dependencies.
- **Environment-Driven Configuration**: Configure server endpoints globally via `MINIGIT_SERVER_URL` without retyping URLs.
- **Git-Compatible Core**: Blob object storage, SHA-256 hashing, staging area (index), commit histories, diffs, and trees.
- **Multi-Account Server**: Isolated user workspaces (`/repos/<username>/<repo>`), JSON Web Tokens (JWT), and PBKDF2 password security.
- **Email OTP Verification**: Real-time 6-digit email OTP verification during registration.
- **Remote Collaboration**: Push, pull, and clone repositories across servers with compression and conflict tracking.
- **Ready for Dokploy / Docker**: Deploy the server to any VPS or cloud provider in 1-click using Dokploy.

---

## 🚀 Quick Client Installation

You don't need Python installed. Run the 1-line installer for your operating system:

### Linux & macOS
```bash
curl -fsSL https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/install.sh | bash
```
*To activate immediately in your current terminal session:*
```bash
export PATH="$HOME/.minigit/bin:$PATH"
```

### Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/install.ps1 | iex
```

### Windows (Command Prompt / cmd.exe)
```cmd
powershell -c "irm https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/install.ps1 | iex"
```

> **Manual Downloads**: Prebuilt binaries for all architectures (x86_64, arm64) are also available directly on [GitHub Releases](https://github.com/Anirban-dev/Git/releases).

---

## ⚙️ Environment Variables

MiniGit CLI and Server respect the following environment variables:

| Variable | Target | Description | Default |
| :--- | :--- | :--- | :--- |
| `MINIGIT_SERVER_URL` | CLI | Remote MiniGit server endpoint | `http://localhost:3000` |
| `MINIGIT_DEFAULT_BRANCH` | CLI | Default branch name on initialization | `main` |
| `MINIGIT_SECRET_KEY` | Server | Secret key used for signing JWT tokens | *(Required in Production)* |
| `MINIGIT_SERVER_PORT` | Server | HTTP port for server process | `3000` |
| `EMAIL_USER` | Server | Gmail address for sending registration OTPs | *(Optional)* |
| `EMAIL_PASS` | Server | Gmail App Password for SMTP authentication | *(Optional)* |

> 💡 **Setting your default server URL:**
> - **Linux / macOS**: `export MINIGIT_SERVER_URL="https://git.yourdomain.com"` (add to `~/.bashrc` or `~/.zshrc`)
> - **Windows (PowerShell)**: `[Environment]::SetEnvironmentVariable("MINIGIT_SERVER_URL", "https://git.yourdomain.com", "User")`
> - **Windows (CMD)**: `setx MINIGIT_SERVER_URL "https://git.yourdomain.com"`

---

## 🛠️ Usage Guide

### 1. User Authentication

#### Register a New Account (with Email OTP)
```bash
# Uses $MINIGIT_SERVER_URL or specify --server directly
minigit auth register
```
*Prompts for username, email, and password. An OTP will be emailed to verify your account.*

#### Log In
```bash
minigit auth login
```

#### Check Authentication Status
```bash
minigit auth status
```

#### Log Out
```bash
minigit auth logout
```

---

### 2. Local Repository Workflow

```bash
# 1. Initialize a new MiniGit repository
mkdir my-project
cd my-project
minigit init

# 2. Create some files
echo "# My First Project" > README.md
echo "print('Hello MiniGit!')" > app.py

# 3. Check status of untracked files
minigit status

# 4. Stage files for commit
minigit add .

# 5. Commit changes with a message
minigit commit -m "Initial commit"

# 6. View commit logs
minigit log

# 7. Check line-by-line diffs
echo "print('Updated version')" >> app.py
minigit diff
```

---

### 3. Remote Repositories & Collaboration

#### Add Remote and Auto-Create on Server
```bash
# If MINIGIT_SERVER_URL is set to https://git.yourdomain.com:
minigit remote add origin $MINIGIT_SERVER_URL/repos/<username>/my-project --create
```

#### Push Commits to Server
```bash
minigit push origin main
```

#### Clone a Remote Repository
```bash
minigit clone $MINIGIT_SERVER_URL/repos/<username>/my-project cloned-project
```

#### Pull Latest Changes
```bash
cd cloned-project
minigit pull
```

---

## ☁️ Server Deployment (Dokploy & Docker)

MiniGit Server is container-ready for **Dokploy**:

1. In Dokploy, click **Create Application** $\rightarrow$ select repository `Anirban-dev/Git`.
2. Set **Build Type**: `Dockerfile` (located at `Dockerfile`).
3. Set **Environment Variables**:
   ```env
   MINIGIT_SECRET_KEY=your-secure-random-secret-key
   MINIGIT_SERVER_PORT=3000
   EMAIL_USER=your-email@gmail.com
   EMAIL_PASS=your-gmail-app-password
   ```
4. Add a **Persistent Volume Mount**:
   - **Host Path**: `minigit_storage` $\rightarrow$ **Mount Path**: `/app/storage`
5. Set your domain and click **Deploy**.

For detailed server deployment instructions, see [docs/INSTALLATION.md](docs/INSTALLATION.md).

---

## 🗑️ Uninstallation

To completely remove the MiniGit CLI and clean your `PATH`:

- **Linux / macOS**:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/uninstall.sh | bash
  ```
- **Windows**:
  ```powershell
  irm https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/uninstall.ps1 | iex
  ```

---

## 📚 Documentation

- [Installation & Deployment Guide](docs/INSTALLATION.md)
- [CLI User Guide](docs/USER_GUIDE.md)
- [Architecture & Internal Engine](docs/ARCHITECTURE.md)
- [HTTP API Reference](docs/API.md)

---

## 📄 License

Distributed under the MIT License.
