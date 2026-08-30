# MiniGit Terminal User Guide

This guide covers full terminal usage for the MiniGit CLI client (`minigit.py`) and HTTP Server (`minigit_server.py`).

---

## 1. Starting the MiniGit Server

Start the multi-account server on port 3000:
```bash
python minigit_server.py --port 3000
```

---

## 2. User Authentication

The CLI uses the `MINIGIT_SERVER_URL` environment variable by default, or you can supply `--server <url>`.

### Register a New Account (with Email OTP):
```bash
# Uses $MINIGIT_SERVER_URL, or pass --server
minigit auth register
# OR
minigit auth register --server https://git.yourdomain.com
```

### Log In to Existing Account:
```bash
minigit auth login
# OR
minigit auth login --server https://git.yourdomain.com
```

### Check Authentication Status:
```bash
minigit auth status
# OR
minigit auth status --server https://git.yourdomain.com
```

### Log Out (Clears Saved Credentials):
```bash
minigit auth logout
```

---

## 3. Local Version Control Workflow

### Initialize a Local Repository:
```bash
mkdir my-app
cd my-app
minigit init
```

### Create & Edit Files:
```bash
echo "# My App" > README.md
echo "print('Hello MiniGit')" > main.py
```

### Check Repository Status:
```bash
minigit status
```

### Stage Files:
```bash
minigit add .
```

### Commit Changes:
```bash
minigit commit -m "Initial commit"
```

### View Commit History:
```bash
minigit log
```

### View Line-by-Line Diffs:
```bash
echo "print('Updated')" >> main.py
minigit diff
```

---

## 4. Remote Collaboration & Push/Pull

### Configure Remote Repository:
```bash
minigit remote add origin $MINIGIT_SERVER_URL/repos/<username>/my-app --create
```

### Push Local Commits to Server:
```bash
minigit push
```

### Clone Remote Repository:
```bash
minigit clone $MINIGIT_SERVER_URL/repos/<username>/my-app cloned-app
```

### Pull Latest Changes:
```bash
cd cloned-app
minigit pull
```

### Show Help for All Commands:
```bash
minigit help
```
