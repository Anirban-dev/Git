import os
import json
import threading
import uuid
from .config import DB_FILE, ensure_storage_dirs

class Database:
    def __init__(self):
        self.lock = threading.Lock()
        ensure_storage_dirs()
        self._load()

    def _load(self):
        if os.path.isfile(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {"users": [], "tokens": [], "repos": []}
        else:
            self.data = {"users": [], "tokens": [], "repos": []}
            self._save()

    def _save(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def find_user_by_username(self, username: str) -> dict | None:
        with self.lock:
            u_lower = username.lower()
            for u in self.data["users"]:
                if u["username"].lower() == u_lower:
                    return u
            return None

    def find_user_by_email(self, email: str) -> dict | None:
        with self.lock:
            e_lower = email.lower()
            for u in self.data["users"]:
                if u["email"].lower() == e_lower:
                    return u
            return None

    def find_user_by_id(self, user_id: str) -> dict | None:
        with self.lock:
            for u in self.data["users"]:
                if u["id"] == user_id:
                    return u
            return None

    def create_user(self, username: str, email: str, password_hash: str) -> dict:
        with self.lock:
            user = {
                "id": str(uuid.uuid4()),
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "created_at": os.environ.get("TIMESTAMP") or "2026-08-13T12:00:00Z"
            }
            self.data["users"].append(user)
            self._save()
            return user

    def create_token(self, user_id: str, token_str: str, name: str) -> dict:
        with self.lock:
            token_obj = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "token": token_str,
                "token_prefix": token_str[:8],
                "name": name,
                "created_at": "2026-08-13T12:00:00Z"
            }
            self.data["tokens"].append(token_obj)
            self._save()
            return token_obj

    def find_token_by_str(self, token_str: str) -> dict | None:
        with self.lock:
            for t in self.data["tokens"]:
                if t["token"] == token_str:
                    return t
            return None

    def find_tokens_by_user(self, user_id: str) -> list[dict]:
        with self.lock:
            return [t for t in self.data["tokens"] if t["user_id"] == user_id]

    def revoke_token(self, token_id: str, user_id: str) -> bool:
        with self.lock:
            initial_len = len(self.data["tokens"])
            self.data["tokens"] = [t for t in self.data["tokens"] if not (t["id"] == token_id and t["user_id"] == user_id)]
            if len(self.data["tokens"]) < initial_len:
                self._save()
                return True
            return False

    def find_repo(self, owner: str, name: str) -> dict | None:
        with self.lock:
            o_lower, n_lower = owner.lower(), name.lower()
            for r in self.data["repos"]:
                if r["owner"].lower() == o_lower and r["name"].lower() == n_lower:
                    return r
            return None

    def create_repo(self, owner: str, name: str, description: str = "", visibility: str = "public") -> dict:
        with self.lock:
            existing = self.find_repo(owner, name)
            if existing:
                return existing

            repo = {
                "id": str(uuid.uuid4()),
                "owner": owner,
                "name": name,
                "description": description,
                "visibility": visibility,
                "created_at": "2026-08-13T12:00:00Z"
            }
            self.data["repos"].append(repo)
            self._save()
            return repo

    def list_public_or_user_repos(self, current_username: str | None = None) -> list[dict]:
        with self.lock:
            result = []
            for r in self.data["repos"]:
                if r["visibility"] == "public" or (current_username and r["owner"].lower() == current_username.lower()):
                    result.append(r)
            return result

db = Database()
