import sys
import getpass
import os
import time
import json
from ..core.config import load_global_credentials, save_global_credentials, clear_global_credentials, get_server_url, validate_server_url
from ..remote.client import register_user, login_user, verify_otp

def cmd_auth(args):
    sub = args.auth_cmd
    server_url = validate_server_url(getattr(args, "server", None))

    if sub == "register":
        username = input("Username: ").strip()
        email = input("Email: ").strip()
        password = getpass.getpass("Password: ")

        # Register user on server (generates OTP and creates user)
        res = register_user(server_url, username, email, password)
        
        if "error" in res:
            print(f"Error during registration: {res['error']}")
            sys.exit(1)

        email_sent = res.get("email_sent", "unknown")
        if email_sent == "failed":
            print("Warning: OTP email could not be sent. Check server logs or EMAIL_USER/EMAIL_PASS configuration.")
        else:
            print(f"OTP code has been sent to {email}. Please check your inbox / spam folder.")
        
        # Ask user to enter the OTP
        otp_code = input("Enter OTP code sent to your email: ").strip()
        
        # Verify OTP with server to finalize user creation
        otp_res = verify_otp(server_url, email, otp_code)
        
        if otp_res.get("status") == "OTP verified" and "token" in otp_res:
            save_global_credentials({
                "token": otp_res["token"],
                "user": otp_res["user"],
                "server": server_url
            })
            print(f"User registered & logged in as '{otp_res['user']['username']}'")
        elif otp_res.get("status") == "OTP verified":
            print("OTP verified successfully.")
        else:
            print(f"Error: {otp_res.get('error', 'Invalid OTP code')}")
            sys.exit(1)

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
            print(f"Server: {creds.get('server', get_server_url())}")
        else:
            print("Not authenticated. Use 'minigit auth login' or 'minigit auth register'.")
