# MiniGit Core Architecture

MiniGit is a modular, high-performance distributed version control system built in pure Python with zero external pip dependencies.

## System Components

```
+-------------------------------------------------------+
|                    MiniGit CLI                        |
|  (minigit.py / minigit_cli module)                    |
|                                                       |
|  - Content-Addressed Object Engine (zlib + SHA-1)     |
|  - Index & Working Tree Diff Tracker                  |
|  - Local Config & Credentials Store (~/.minigit_creds) |
+---------------------------+---------------------------+
                            |
                     HTTP / JSON Protocol
                            |
+---------------------------v---------------------------+
|                    MiniGit Server                     |
|  (minigit_server.py / minigit_server module)          |
|                                                       |
|  - Multi-Threaded HTTP Server (0.0.0.0:3000)          |
|  - PBKDF2 Password Hashing & Bearer Token Auth        |
|  - Multi-Account Repository Isolation                 |
|    └─ ./storage/repos/<username>/<reponame>/          |
|  - Object Graph & Fast-Forward Push Validator          |
|  - On-the-fly ZIP Archive Generator                   |
+-------------------------------------------------------+
```

## Directory Structure

### 1. CLI Client Architecture (`minigit_cli/`)
- **`main.py`**: Lightweight CLI entry point, argument parser, and command dispatcher (~80 lines).
- **`commands/auth.py`**: Command handlers for user login, registration, logout, token generation, and status.
- **`commands/local.py`**: Local version control operations (`init`, `add`, `commit`, `status`, `log`, `diff`).
- **`commands/remote.py`**: Remote server interaction operations (`remote`, `push`, `pull`, `clone`).
- **`core/objects.py`**: Handles SHA-1 object hashing, zlib stream compression, tree construction, and commit formatting.
- **`core/repository.py`**: Manages `.minigit` directory structure, index serialization, working tree file status computation, and tree file extraction.
- **`core/ignore.py`**: Evaluates `.miniignore` file patterns using glob wildcard matching.
- **`core/config.py`**: Manages global authentication state (`~/.minigit_credentials`) and local repository remotes (`.minigit/config`).
- **`remote/client.py`**: Standard library HTTP client for registration, login, token management, cloning, pushing, and pulling.
- **`remote/protocol.py`**: Traverses commit graphs to collect reachable object payloads for network transport.

### 2. Server Architecture (`minigit_server/`)
- **`config.py`**: Configures storage paths (`./storage/repos`) and token signing keys.
- **`db.py`**: Thread-safe persistent storage for accounts, personal access tokens, and repository registry (`./storage/db.json`).
- **`auth.py`**: Implements salted PBKDF2 SHA-256 password hashing (100,000 iterations) and HMAC-signed Bearer/PAT validation.
- **`git_engine.py`**: Controls multi-tenant user repository isolation (`storage/repos/<owner>/<repo>`), object graph storage, branch head tracking, and zip exports.
- **`handlers/router.py`**: Serves HTTP routes for registration, login, repository creation, push protocol, pull protocol, and zip downloads.

## Security & Repository Isolation
Each user's repository resides under a strictly isolated directory namespace:
`./storage/repos/<username>/<reponame>/.minigit/`

- **Read Access**: Public repositories are readable by anyone; private repositories require Bearer or PAT authentication.
- **Write Access**: Pushing commits requires authentication matching the namespace owner (`<username>`).
