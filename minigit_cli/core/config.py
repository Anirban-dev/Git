import os
import json

GLOBAL_CREDENTIALS_FILE = os.path.expanduser("~/.minigit_credentials")

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
