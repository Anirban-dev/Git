import os

STORAGE_DIR = os.path.abspath("./storage")
REPOS_DIR = os.path.join(STORAGE_DIR, "repos")
DB_FILE = os.path.join(STORAGE_DIR, "db.json")
SECRET_KEY = "minigit_super_secret_jwt_key_2026"

def ensure_storage_dirs():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    os.makedirs(REPOS_DIR, exist_ok=True)
