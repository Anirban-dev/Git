import json
import urllib.request
import urllib.error
import os
from ..core.config import load_global_credentials

def http_request(url: str, method: str = "GET", data: dict | None = None, token: str | None = None) -> dict:
    """
    Standard library HTTP JSON wrapper.
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "MiniGit-CLI/2.0"
    }

    if not token:
        creds = load_global_credentials()
        token = creds.get("token")

    if token:
        headers["Authorization"] = f"Bearer {token}"

    body_bytes = None
    if data is not None:
        body_bytes = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            if resp_body:
                return json.loads(resp_body)
            return {}
    except urllib.error.HTTPError as e:
        server_error = None
        try:
            raw_body = e.read()
            if raw_body:
                err_json = json.loads(raw_body.decode("utf-8"))
                server_error = err_json.get("error") or err_json.get("message")
        except Exception:
            pass

        if server_error:
            raise RuntimeError(server_error)
        raise RuntimeError(f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection failed to {url}: {e.reason}")

def register_user(server_url: str, username: str, email: str, password: str) -> dict:
    endpoint = f"{server_url.rstrip('/')}/api/auth/register"
    return http_request(endpoint, method="POST", data={
        "username": username,
        "email": email,
        "password": password
    })

def login_user(server_url: str, username_or_email: str, password: str) -> dict:
    endpoint = f"{server_url.rstrip('/')}/api/auth/login"
    return http_request(endpoint, method="POST", data={
        "username": username_or_email,
        "password": password
    })

def create_personal_access_token(server_url: str, name: str) -> dict:
    endpoint = f"{server_url.rstrip('/')}/api/auth/tokens"
    return http_request(endpoint, method="POST", data={"name": name})

def create_remote_repo(server_url: str, name: str, description: str = "", visibility: str = "public") -> dict:
    endpoint = f"{server_url.rstrip('/')}/api/repos/create"
    return http_request(endpoint, method="POST", data={
        "name": name,
        "description": description,
        "visibility": visibility
    })

def push_to_remote(remote_url: str, branch: str, commit_sha: str, objects: list[dict]) -> dict:
    endpoint = f"{remote_url.rstrip('/')}/push"
    return http_request(endpoint, method="POST", data={
        "branch": branch,
        "commit_sha": commit_sha,
        "objects": objects
    })

def pull_from_remote(remote_url: str, branch: str = "main") -> dict:
    endpoint = f"{remote_url.rstrip('/')}/pull?branch={branch}"
    return http_request(endpoint, method="GET")

def fetch_remote_info(remote_url: str) -> dict:
    endpoint = f"{remote_url.rstrip('/')}/info"
    return http_request(endpoint, method="GET")

def verify_otp(server_url: str, email: str, otp_code: str) -> dict:
    """Verify OTP code with the server."""
    endpoint = f"{server_url.rstrip('/')}/api/auth/otp/verify"
    return http_request(endpoint, method="POST", data={
        "email": email,
        "otp_code": otp_code
    }, token=None)  # OTP verification is a public endpoint
