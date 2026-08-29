import os
import json
import threading
import uuid
import time
from .config import DB_FILE, ensure_storage_dirs
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        self.lock = threading.RLock()  # RLock allows re-entrant locking from the same thread
        ensure_storage_dirs()
        self._load()

    def _load(self):
        if os.path.isfile(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {"users": [], "tokens": [], "repos": [], "otps": []}
        else:
            self.data = {"users": [], "tokens": [], "repos": [], "otps": []}
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

    # Pending registration methods
    def create_pending_user(self, username: str, email: str, password_hash: str, otp_code: str) -> dict:
        with self.lock:
            self._cleanup_expired_otps()
            if "pending_users" not in self.data:
                self.data["pending_users"] = []

            # Remove any existing pending registration for this email or username
            u_lower = username.lower()
            e_lower = email.lower()
            self.data["pending_users"] = [
                p for p in self.data["pending_users"]
                if p["email"].lower() != e_lower and p["username"].lower() != u_lower
            ]

            pending_obj = {
                "id": str(uuid.uuid4()),
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "otp": otp_code,
                "created_at": time.time(),
                "expires_at": time.time() + 300  # 5 minutes expiry
            }
            self.data["pending_users"].append(pending_obj)
            self._save()
            return pending_obj

    def find_pending_user(self, email: str) -> dict | None:
        with self.lock:
            self._cleanup_expired_otps()
            if "pending_users" not in self.data:
                return None
            e_lower = email.lower()
            now = time.time()
            for p in self.data["pending_users"]:
                if p["email"].lower() == e_lower and now < p["expires_at"]:
                    return p
            return None

    def delete_pending_user(self, email: str) -> bool:
        with self.lock:
            if "pending_users" not in self.data:
                return False
            e_lower = email.lower()
            initial_len = len(self.data["pending_users"])
            self.data["pending_users"] = [p for p in self.data["pending_users"] if p["email"].lower() != e_lower]
            if len(self.data["pending_users"]) < initial_len:
                self._save()
                return True
            return False

    def activate_pending_user(self, email: str, otp_code: str) -> dict | None:
        with self.lock:
            self._cleanup_expired_otps()
            if "pending_users" not in self.data:
                return None
            e_lower = email.lower()
            now = time.time()
            matched = None
            for p in self.data["pending_users"]:
                if p["email"].lower() == e_lower and now < p["expires_at"]:
                    if p["otp"] == otp_code:
                        matched = p
                        break
            if not matched:
                return None

            # Remove from pending
            self.data["pending_users"] = [p for p in self.data["pending_users"] if p["email"].lower() != e_lower]

            # Create the actual active user
            user = {
                "id": matched["id"],
                "username": matched["username"],
                "email": matched["email"],
                "password_hash": matched["password_hash"],
                "created_at": os.environ.get("TIMESTAMP") or "2026-08-13T12:00:00Z"
            }
            self.data["users"].append(user)
            self._save()
            return user

    # OTP methods for email verification
    def _cleanup_expired_otps(self):
        """Remove all expired OTPs and expired pending registrations from the database."""
        with self.lock:
            now = time.time()
            if "pending_users" in self.data:
                self.data["pending_users"] = [p for p in self.data["pending_users"] if p.get("expires_at", 0) > now]
            expired_count = 0
            for o in self.data["otps"]:
                if now >= o.get("expires_at", 0):
                    expired_count += 1
            if expired_count > 0:
                self.data["otps"] = [o for o in self.data["otps"] if o.get("expires_at", 0) > now]
                self._save()
                return expired_count
            return 0

    def create_otp(self, email: str, otp_code: str) -> dict:
        with self.lock:
            # Clean up any expired OTPs first
            self._cleanup_expired_otps()
            
            otp_obj = {
                "id": str(uuid.uuid4()),
                "email": email,
                "otp": otp_code,
                "created_at": time.time(),
                "expires_at": time.time() + 300  # 5 minutes expiry
            }
            # Remove any existing OTP for this email
            self.data["otps"] = [o for o in self.data["otps"] if o["email"] != email]
            self.data["otps"].append(otp_obj)
            self._save()
            return otp_obj

    def verify_otp(self, email: str, otp_code: str) -> bool:
        with self.lock:
            # Clean up expired OTPs first
            self._cleanup_expired_otps()
            
            for o in self.data["otps"]:
                if o["email"] == email and time.time() < o["expires_at"]:
                    if o["otp"] == otp_code:
                        # Remove OTP after successful verification
                        self.data["otps"] = [ot for ot in self.data["otps"] if ot["email"] != email]
                        self._save()
                        return True
            return False

    def find_otp(self, email: str) -> dict | None:
        with self.lock:
            # Clean up expired OTPs first
            self._cleanup_expired_otps()
            
            for o in self.data["otps"]:
                if o["email"] == email and time.time() < o["expires_at"]:
                    return o
            return None

db = Database()
