import sys
import getpass
from ..core.config import load_global_credentials, save_global_credentials, clear_global_credentials
from ..remote.client import register_user, login_user, create_personal_access_token

DEFAULT_SERVER_URL = "http://localhost:3000"

def cmd_auth(args):
    sub = args.auth_cmd
    server_url = args.server or DEFAULT_SERVER_URL

    if sub == "register":
        username = input("Username: ").strip()
        email = input("Email: ").strip()
        password = getpass.getpass("Password: ")
        res = register_user(server_url, username, email, password)
        save_global_credentials({
            "token": res["token"],
            "user": res["user"],
            "server": server_url
        })
        print(f"Registered & logged in as '{res['user']['username']}'")

    elif sub == "login":
        username = input("Username or Email: ").strip()
        password = getpass.getpass("Password: ")
        res = login_user(server_url, username, password)
        save_global_credentials({
            "token": res["token"],
            "user": res["user"],
            "server": server_url
        })
        print(f"Successfully logged in as '{res['user']['username']}'")

    elif sub == "logout":
        clear_global_credentials()
        print("Logged out. Credentials cleared.")

    elif sub == "status":
        creds = load_global_credentials()
        if creds.get("token") and creds.get("user"):
            u = creds["user"]
            print(f"Authenticated as: {u.get('username')} ({u.get('email')})")
            print(f"Server: {creds.get('server', DEFAULT_SERVER_URL)}")
        else:
            print("Not authenticated. Use 'minigit auth login' or 'minigit auth register'.")

    elif sub == "token":
        creds = load_global_credentials()
        if not creds.get("token"):
            print("Error: Must be logged in to generate Personal Access Tokens.")
            sys.exit(1)
        token_name = input("Token Name (e.g. Work Laptop): ").strip()
        res = create_personal_access_token(creds.get("server", DEFAULT_SERVER_URL), token_name)
        print("Personal Access Token generated:")
        print(f"  Token: {res['token']}")
        print("Save this token now. It will not be shown again.")
