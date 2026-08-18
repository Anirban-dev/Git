# MiniGit Server HTTP API Specification

The MiniGit HTTP server runs by default on port `3000` and accepts standard JSON HTTP requests.

---

## 1. System & Health

### `GET /` or `GET /api/health`
Returns server status and CLI quickstart guide.

**Response (200 OK):**
```json
{
  "system": "MiniGit Multi-Account Version Control Server",
  "version": "2.0.0",
  "status": "online",
  "cli_download": "minigit",
  "quickstart": { ... }
}
```

---

## 2. Authentication Endpoints

### `POST /api/auth/register`
Registers a new user account.

**Request Body:**
```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "secretpassword"
}
```

**Response (200 OK):**
```json
{
  "token": "<bearer_jwt_token>",
  "user": {
    "id": "uuid",
    "username": "alice",
    "email": "alice@example.com"
  }
}
```

---

### `POST /api/auth/login`
Authenticates a user and returns a session token.

**Request Body:**
```json
{
  "username": "alice",
  "password": "secretpassword"
}
```

---

### `GET /api/auth/me`
Returns current authenticated user details. Requires `Authorization: Bearer <token>`.

---

### `POST /api/auth/tokens`
Generates a new Personal Access Token (`mgp_...`). Requires Bearer token.

**Request Body:**
```json
{
  "name": "CI/CD Token"
}
```

---

### `DELETE /api/auth/tokens/<id>`
Revokes a Personal Access Token.

---

## 3. Repository Management Endpoints

### `GET /api/repos`
Lists public repositories or private repositories belonging to the authenticated user.

---

### `POST /api/repos/create`
Creates a new repository under the user's namespace.

**Request Body:**
```json
{
  "name": "my-project",
  "description": "My project description",
  "visibility": "public"
}
```

---

## 4. Git Transport Protocol Endpoints

### `GET /repos/<owner>/<repo>/info`
Returns branch refs and head commit SHA.

---

### `POST /repos/<owner>/<repo>/push`
Pushes commit object graph to server. Requires `Authorization: Bearer <token>`.

**Request Body:**
```json
{
  "branch": "main",
  "commit_sha": "a1b2c3d...",
  "objects": [
    {
      "sha": "a1b2c3d...",
      "type": "commit",
      "content_hex": "..."
    }
  ]
}
```

---

### `GET /repos/<owner>/<repo>/pull?branch=main`
Fetches objects and head commit for pulling/cloning.

---

### `GET /repos/<owner>/<repo>/archive.zip`
Downloads full repository tree snapshot as a ZIP archive.
