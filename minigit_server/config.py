import os
from dotenv import load_dotenv

load_dotenv()

STORAGE_DIR = "./storage"
REPOS_DIR = os.path.join(STORAGE_DIR, "repos")
DB_FILE = os.path.join(STORAGE_DIR, "db.json")

SECRET_KEY = os.environ.get("MINIGIT_SECRET_KEY", "").strip().strip("\"'")
if not SECRET_KEY:
    raise ValueError(
        "MINIGIT_SECRET_KEY environment variable is required. "
        "Set it in your .env file with a strong random key."
    )

# Email Configuration (Gmail)
EMAIL_USER = os.environ.get("EMAIL_USER", "").strip().strip("\"'")
EMAIL_PASS = os.environ.get("EMAIL_PASS", "").strip().strip("\"'").replace(" ", "")
EMAIL_FROM = EMAIL_USER  # Automatically matches your Gmail address

if not EMAIL_USER or not EMAIL_PASS:
    print("Warning: EMAIL_USER and EMAIL_PASS are not set. OTP verification will not work via email.")
    print("Set these in your .env file to enable email OTP functionality.")

def ensure_storage_dirs():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    os.makedirs(REPOS_DIR, exist_ok=True)