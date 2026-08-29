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

### Register a New Account:
```bash
minigit auth register
```

### Log In to Existing Account:
```bash
minigit auth login
```

### Check Authentication Status:
```bash
minigit auth status
```

### Generate a Personal Access Token (PAT):
*Removed - use `minigit auth login` to authenticate instead*

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
minigit remote add origin http://localhost:3000/repos/<username>/my-app --create
```

### Push Local Commits to Server:
```bash
minigit push
```

### Clone Remote Repository:
```bash
minigit clone http://localhost:3000/repos/<username>/my-app cloned-app
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
