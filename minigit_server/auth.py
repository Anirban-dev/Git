import hashlib
import hmac
import json
import base64
import time
import secrets
from .config import SECRET_KEY
from .db import db

def hash_password(password: str, salt: str | None = None) -> str:
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}${key.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, key_hex = stored_hash.split("$", 1)
        check_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return hmac.compare_digest(check_key.hex(), key_hex)
    except Exception:
        return False

def generate_jwt(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).decode("utf-8").rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
    
    signature_base = f"{header_b64}.{payload_b64}"
    sig = hmac.new(SECRET_KEY.encode("utf-8"), signature_base.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")

    return f"{signature_base}.{sig_b64}"

def decode_jwt(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts
        signature_base = f"{header_b64}.{payload_b64}"

        sig_check = hmac.new(SECRET_KEY.encode("utf-8"), signature_base.encode("utf-8"), hashlib.sha256).digest()
        sig_check_b64 = base64.urlsafe_b64encode(sig_check).decode("utf-8").rstrip("=")

        if not hmac.compare_digest(sig_b64, sig_check_b64):
            return None

        # Add back padding if needed
        padding = "=" * (4 - len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes.decode("utf-8"))

        if "exp" in payload and time.time() > payload["exp"]:
            return None

        return payload
    except Exception:
        return None

def authenticate_request(headers: dict) -> dict | None:
    """
    Extracts Bearer token or Personal Access Token from Authorization header.
    Returns user dict or None.
    """
    auth_header = headers.get("Authorization") or headers.get("authorization")
    if not auth_header:
        return None

    if not auth_header.startswith("Bearer "):
        return None

    raw_token = auth_header[7:].strip()

    # 1. Check if it's a PAT
    pat = db.find_token_by_str(raw_token)
    if pat:
        return db.find_user_by_id(pat["user_id"])

    # 2. Check if it's a JWT
    jwt_data = decode_jwt(raw_token)
    if jwt_data and "user_id" in jwt_data:
        return db.find_user_by_id(jwt_data["user_id"])

    return None
