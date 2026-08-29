import os
import json

GLOBAL_CREDENTIALS_FILE = os.path.expanduser("~/.minigit_credentials")

# Environment variable configuration
MINIGIT_SERVER_URL = os.environ.get("MINIGIT_SERVER_URL", "http://localhost:3000")
MINIGIT_DEFAULT_BRANCH = os.environ.get("MINIGIT_DEFAULT_BRANCH", "main")
MINIGIT_SECRET_KEY = os.environ.get("MINIGIT_SECRET_KEY", "minigit_super_secret_jwt_key_2026")

def load_global_credentials() -> dict:
    if os.path.isfile(GLOBAL_CREDENTIALS_FILE):
        try:
            with open(GLOBAL_CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_global_credentials(data: dict):
    os.makedirs(os.path.dirname(GLOBAL_CREDENTIALS_FILE), exist_ok=True)
    existing = load_global_credentials()
    existing.update(data)
    with open(GLOBAL_CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

def clear_global_credentials():
    if os.path.isfile(GLOBAL_CREDENTIALS_FILE):
        try:
            os.remove(GLOBAL_CREDENTIALS_FILE)
        except Exception:
            pass

def load_local_config(repo_path: str) -> dict:
    cfg_file = os.path.join(repo_path, ".minigit", "config")
    if os.path.isfile(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_local_config(repo_path: str, data: dict):
    cfg_file = os.path.join(repo_path, ".minigit", "config")
    existing = load_local_config(repo_path)
    existing.update(data)
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

def validate_server_url(url: str | None) -> str:
    """
    Validate and return the server URL.
    Requires an explicit http:// or https:// protocol.
    """
    if not url:
        url = os.environ.get("MINIGIT_SERVER_URL", MINIGIT_SERVER_URL)
    
    url = url.strip()
    if not url.startswith("https://") and not url.startswith("http://"):
        raise ValueError(
            f"Invalid server URL '{url}'. Server URL must include protocol (e.g. 'https://{url}')."
        )
    return url.rstrip('/')

def get_server_url() -> str:
    """Get the validated server URL from environment variable or default."""
    return validate_server_url(os.environ.get("MINIGIT_SERVER_URL", MINIGIT_SERVER_URL))

def get_default_branch() -> str:
    """Get the default branch name from environment variable or default."""
    return MINIGIT_DEFAULT_BRANCH
