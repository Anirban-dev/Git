import json
import urllib.parse
from http.server import BaseHTTPRequestHandler
from ..db import db
from ..auth import hash_password, verify_password, generate_jwt, authenticate_request
from ..git_engine import (
    ensure_server_repo,
    store_raw_object,
    get_repo_ref,
    update_repo_ref,
    collect_server_objects,
    create_zip_archive_bytes
)

class MiniGitRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, data: dict):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, status: int, content_type: str, data: bytes, filename: str | None = None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)

    def _read_body_json(self) -> dict:
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        body_bytes = self.rfile.read(content_length)
        return json.loads(body_bytes.decode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/')
        query = urllib.parse.parse_qs(parsed.query)

        # 1. Healthcheck & Terminal Banner Root
        if path == "" or path == "/api/health":
            self._send_json(200, {
                "system": "MiniGit Multi-Account Version Control Server",
                "version": "2.0.0",
                "status": "online",
                "cli_download": "minigit",
                "quickstart": {
                    "register": "minigit auth register",
                    "login": "minigit auth login",
                    "init": "minigit init my-repo",
                    "commit": "minigit commit -m 'Initial commit'",
                    "remote": "minigit remote add origin http://localhost:3000/repos/<user>/<repo> --create",
                    "push": "minigit push"
                }
            })
            return

        # 2. Auth: Current User
        if path == "/api/auth/me":
            user = authenticate_request(dict(self.headers))
            if not user:
                self._send_json(401, {"error": "Unauthorized"})
                return
            self._send_json(200, {"user": {"id": user["id"], "username": user["username"], "email": user["email"]}})
            return

        # 3. Auth: List Personal Access Tokens
        if path == "/api/auth/tokens":
            user = authenticate_request(dict(self.headers))
            if not user:
                self._send_json(401, {"error": "Unauthorized"})
                return
            tokens = db.find_tokens_by_user(user["id"])
            self._send_json(200, {"tokens": tokens})
            return

        # 4. Repositories: List public / owned repos
        if path == "/api/repos":
            user = authenticate_request(dict(self.headers))
            username = user["username"] if user else None
            repos = db.list_public_or_user_repos(username)
            self._send_json(200, {"repos": repos})
            return

        # 5. Git Protocol Info: /repos/<owner>/<repo>/info
        if path.startswith("/repos/") and path.endswith("/info"):
            parts = path.split("/")
            if len(parts) == 5:
                owner, repo_name = parts[2], parts[3]
                repo = db.find_repo(owner, repo_name)
                if not repo:
                    self._send_json(404, {"error": "Repository not found"})
                    return

                repo_path = ensure_server_repo(owner, repo_name)
                head_commit = get_repo_ref(repo_path, "main")
                self._send_json(200, {
                    "owner": owner,
                    "name": repo_name,
                    "visibility": repo["visibility"],
                    "head_commit": head_commit
                })
                return

        # 6. Git Protocol Pull: /repos/<owner>/<repo>/pull
        if path.startswith("/repos/") and path.endswith("/pull"):
            parts = path.split("/")
            if len(parts) == 5:
                owner, repo_name = parts[2], parts[3]
                branch = query.get("branch", ["main"])[0]

                repo = db.find_repo(owner, repo_name)
                if not repo:
                    self._send_json(404, {"error": "Repository not found"})
                    return

                # Private repo check
                if repo["visibility"] == "private":
                    user = authenticate_request(dict(self.headers))
                    if not user or user["username"].lower() != owner.lower():
                        self._send_json(403, {"error": "Access denied to private repository"})
                        return

                repo_path = ensure_server_repo(owner, repo_name)
                head_sha = get_repo_ref(repo_path, branch)

                if not head_sha:
                    self._send_json(200, {"branch": branch, "head_commit": None, "objects": []})
                    return

                objects = collect_server_objects(repo_path, head_sha)
                self._send_json(200, {
                    "branch": branch,
                    "head_commit": head_sha,
                    "objects": objects
                })
                return

        # 7. Download ZIP archive: /repos/<owner>/<repo>/archive.zip
        if path.startswith("/repos/") and path.endswith("/archive.zip"):
            parts = path.split("/")
            if len(parts) == 5:
                owner, repo_name = parts[2], parts[3]
                repo = db.find_repo(owner, repo_name)
                if not repo:
                    self._send_json(404, {"error": "Repository not found"})
                    return

                repo_path = ensure_server_repo(owner, repo_name)
                head_sha = get_repo_ref(repo_path, "main")
                if not head_sha:
                    self._send_json(400, {"error": "Repository has no commits to archive"})
                    return

                zip_data = create_zip_archive_bytes(repo_path, head_sha)
                self._send_bytes(200, 'application/zip', zip_data, filename=f"{repo_name}.zip")
                return

        self._send_json(404, {"error": f"Endpoint not found: {path}"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/')

        try:
            body = self._read_body_json()
        except Exception:
            body = {}

        # 1. Auth: Register
        if path == "/api/auth/register":
            username = body.get("username", "").strip()
            email = body.get("email", "").strip()
            password = body.get("password", "").strip()

            if not username or not email or not password:
                self._send_json(400, {"error": "username, email, and password required"})
                return

            if db.find_user_by_username(username):
                self._send_json(400, {"error": f"Username '{username}' already exists"})
                return

            if db.find_user_by_email(email):
                self._send_json(400, {"error": f"Email '{email}' already registered"})
                return

            pwd_hash = hash_password(password)
            user = db.create_user(username, email, pwd_hash)
            token = generate_jwt({"user_id": user["id"], "username": user["username"]})

            self._send_json(200, {
                "token": token,
                "user": {"id": user["id"], "username": user["username"], "email": user["email"]}
            })
            return

        # 2. Auth: Login
        if path == "/api/auth/login":
            username_or_email = body.get("username", "").strip()
            password = body.get("password", "").strip()

            user = db.find_user_by_username(username_or_email) or db.find_user_by_email(username_or_email)
            if not user or not verify_password(password, user["password_hash"]):
                self._send_json(401, {"error": "Invalid username/email or password"})
                return

            token = generate_jwt({"user_id": user["id"], "username": user["username"]})
            self._send_json(200, {
                "token": token,
                "user": {"id": user["id"], "username": user["username"], "email": user["email"]}
            })
            return

        # 3. Auth: Create Personal Access Token
        if path == "/api/auth/tokens":
            user = authenticate_request(dict(self.headers))
            if not user:
                self._send_json(401, {"error": "Unauthorized"})
                return

            name = body.get("name", "CLI Token").strip()
            import secrets
            raw_token = f"mgp_{secrets.token_hex(20)}"
            t_obj = db.create_token(user["id"], raw_token, name)
            self._send_json(200, {
                "id": t_obj["id"],
                "token": raw_token,
                "name": t_obj["name"]
            })
            return

        # 4. Repositories: Create Repo
        if path == "/api/repos/create":
            user = authenticate_request(dict(self.headers))
            if not user:
                self._send_json(401, {"error": "Authentication required to create repository"})
                return

            name = body.get("name", "").strip()
            description = body.get("description", "").strip()
            visibility = body.get("visibility", "public")

            if not name:
                self._send_json(400, {"error": "Repository name is required"})
                return

            repo = db.create_repo(user["username"], name, description, visibility)
            ensure_server_repo(user["username"], name)
            self._send_json(200, {"repo": repo})
            return

        # 5. Git Protocol Push: /repos/<owner>/<repo>/push
        if path.startswith("/repos/") and path.endswith("/push"):
            parts = path.split("/")
            if len(parts) == 5:
                owner, repo_name = parts[2], parts[3]

                # Push requires authentication
                user = authenticate_request(dict(self.headers))
                if not user:
                    self._send_json(401, {"error": "Authentication required to push commits"})
                    return

                if user["username"].lower() != owner.lower():
                    self._send_json(403, {"error": f"You do not have write access to repository '{owner}/{repo_name}'"})
                    return

                repo = db.find_repo(owner, repo_name)
                if not repo:
                    # Auto-create if namespace owner matches
                    repo = db.create_repo(owner, repo_name)

                repo_path = ensure_server_repo(owner, repo_name)

                branch = body.get("branch", "main")
                commit_sha = body.get("commit_sha")
                objects = body.get("objects", [])

                if not commit_sha:
                    self._send_json(400, {"error": "commit_sha is required"})
                    return

                # Store incoming objects
                for obj in objects:
                    content = bytes.fromhex(obj["content_hex"])
                    store_raw_object(repo_path, obj["sha"], obj["type"], content)

                # Update branch reference
                update_repo_ref(repo_path, branch, commit_sha)

                self._send_json(200, {
                    "status": "success",
                    "owner": owner,
                    "repo": repo_name,
                    "branch": branch,
                    "commit_sha": commit_sha,
                    "pushed_objects": len(objects)
                })
                return

        self._send_json(404, {"error": f"Endpoint not found: {path}"})

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/')

        # Revoke token: /api/auth/tokens/<id>
        if path.startswith("/api/auth/tokens/"):
            token_id = path.replace("/api/auth/tokens/", "")
            user = authenticate_request(dict(self.headers))
            if not user:
                self._send_json(401, {"error": "Unauthorized"})
                return

            revoked = db.revoke_token(token_id, user["id"])
            if revoked:
                self._send_json(200, {"status": "revoked"})
            else:
                self._send_json(404, {"error": "Token not found"})
            return

        self._send_json(404, {"error": f"Endpoint not found: {path}"})
