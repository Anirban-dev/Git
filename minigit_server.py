#!/usr/bin/env python
"""
minigit_server — a tiny HTTP server that stores minigit repositories,
acting like a minimal "GitHub" for the minigit tool. No dependencies
beyond the Python standard library.

Repos are stored server-side as bare ".minigit" directories under
STORAGE_DIR (one subfolder per repo name):

    storage/
        <repo-name>/
            objects/<sha1[:2]>/<sha1[2:]>
            refs/heads/main
            HEAD
            config

API
---
GET    /repos                    -> {"repos": [names...]}
PUT    /repos/<name>             -> create a new, empty repo (201) or 409 if it exists
GET    /repos/<name>/head        -> {"head": "<sha1>" | null}
GET    /repos/<name>             -> zip archive of the repo's .minigit dir (clone/pull)
GET    /repos/<name>/archive     -> same as above, explicit form
POST   /repos/<name>/push        -> body: zip archive of a .minigit dir.
                                     Rejected with 409 unless it's a fast-forward
                                     of the repo's current HEAD (add ?force=1 to
                                     override).

Run
---
    python minigit_server.py [--host 0.0.0.0] [--port 8000] [--storage ./storage]

Then, from minigit.py, treat "http://host:port/repos/<name>" as a remote:

    minigit clone http://localhost:8000/repos/demo ./demo
    minigit pull
    minigit push

(A repo must already exist on the server before you can push to it — create
one with:  curl -X PUT http://localhost:8000/repos/demo)
"""

import argparse
import io
import json
import os
import shutil
import zipfile
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

STORAGE_DIR = "storage"


# --------------------------------------------------------------------------
# helpers (mirror the logic in minigit.py, but operate directly on a
# ".minigit" directory rather than a repo root that contains one)
# --------------------------------------------------------------------------

def repo_path(name):
    safe = os.path.basename(name)  # prevent path traversal via "../"
    if not safe or safe in (".", ".."):
        raise ValueError("invalid repo name")
    return os.path.join(STORAGE_DIR, safe)


def read_head(mg_dir):
    head_file = os.path.join(mg_dir, "HEAD")
    if not os.path.exists(head_file):
        return None
    with open(head_file) as f:
        head = f.read().strip()
    if head.startswith("ref: "):
        ref_file = os.path.join(mg_dir, head[5:])
        if not os.path.exists(ref_file):
            return None
        with open(ref_file) as f:
            return f.read().strip() or None
    return head or None


def commit_parent(mg_dir, sha1):
    obj_file = os.path.join(mg_dir, "objects", sha1[:2], sha1[2:])
    with open(obj_file, "rb") as f:
        full = zlib.decompress(f.read())
    _, data = full.split(b"\0", 1)
    return json.loads(data)["parent"]


def is_fast_forward(mg_dir, old_head, new_head):
    """True if old_head is None, equal to new_head, or an ancestor of new_head."""
    if old_head is None or old_head == new_head:
        return True
    cursor = new_head
    while cursor is not None:
        if cursor == old_head:
            return True
        cursor = commit_parent(mg_dir, cursor)
    return False


def zip_dir(path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(path):
            for name in files:
                full = os.path.join(root, name)
                arcname = os.path.relpath(full, path)
                zf.write(full, arcname)
    return buf.getvalue()


def unzip_to(data, dest_dir):
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(dest_dir)


# --------------------------------------------------------------------------
# HTTP handler
# --------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "minigit-server/1.0"

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, data, status=200, content_type="application/zip"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print("[minigit-server]", self.address_string(), "-", fmt % args)

    # ---- GET ------------------------------------------------------------

    def do_GET(self):
        parts = [p for p in urlparse(self.path).path.split("/") if p]

        if parts == ["repos"]:
            names = []
            if os.path.isdir(STORAGE_DIR):
                names = sorted(
                    d for d in os.listdir(STORAGE_DIR)
                    if os.path.isdir(os.path.join(STORAGE_DIR, d))
                )
            return self._send_json({"repos": names})

        if len(parts) == 2 and parts[0] == "repos":
            return self._serve_archive(parts[1])

        if len(parts) == 3 and parts[0] == "repos" and parts[2] == "archive":
            return self._serve_archive(parts[1])

        if len(parts) == 3 and parts[0] == "repos" and parts[2] == "head":
            mg = repo_path(parts[1])
            if not os.path.isdir(mg):
                return self._send_json({"error": "no such repo"}, 404)
            return self._send_json({"head": read_head(mg)})

        self._send_json({"error": "not found"}, 404)

    def _serve_archive(self, name):
        mg = repo_path(name)
        if not os.path.isdir(mg):
            return self._send_json({"error": "no such repo"}, 404)
        self._send_bytes(zip_dir(mg))

    # ---- PUT (create a repo) --------------------------------------------

    def do_PUT(self):
        parts = [p for p in urlparse(self.path).path.split("/") if p]

        if len(parts) == 2 and parts[0] == "repos":
            mg = repo_path(parts[1])
            if os.path.isdir(mg):
                return self._send_json({"error": "repo already exists"}, 409)
            os.makedirs(os.path.join(mg, "objects"), exist_ok=True)
            os.makedirs(os.path.join(mg, "refs", "heads"), exist_ok=True)
            with open(os.path.join(mg, "HEAD"), "w") as f:
                f.write("ref: refs/heads/main\n")
            with open(os.path.join(mg, "config"), "w") as f:
                f.write("{}")
            return self._send_json({"created": parts[1]}, 201)

        self._send_json({"error": "not found"}, 404)

    # ---- POST (push) ------------------------------------------------------

    def do_POST(self):
        parts = [p for p in urlparse(self.path).path.split("/") if p]
        qs = parse_qs(urlparse(self.path).query)

        if len(parts) == 3 and parts[0] == "repos" and parts[2] == "push":
            return self._handle_push(parts[1], force=qs.get("force", ["0"])[0] == "1")

        self._send_json({"error": "not found"}, 404)

    def _handle_push(self, name, force):
        mg = repo_path(name)
        if not os.path.isdir(mg):
            return self._send_json(
                {"error": "no such repo; create it first with PUT /repos/<name>"}, 404
            )

        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)

        tmp_dir = mg + ".incoming"
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir)
        try:
            unzip_to(data, tmp_dir)

            old_head = read_head(mg)
            new_head = read_head(tmp_dir)

            if not force and not is_fast_forward(tmp_dir, old_head, new_head):
                return self._send_json(
                    {"error": "rejected: not a fast-forward of the current HEAD "
                              "(pull first, or retry with ?force=1)"},
                    409,
                )

            # Objects are content-addressed, so a plain union is always safe.
            src_objects = os.path.join(tmp_dir, "objects")
            dst_objects = os.path.join(mg, "objects")
            if os.path.isdir(src_objects):
                for sub in os.listdir(src_objects):
                    src_sub = os.path.join(src_objects, sub)
                    dst_sub = os.path.join(dst_objects, sub)
                    os.makedirs(dst_sub, exist_ok=True)
                    for fname in os.listdir(src_sub):
                        dst_file = os.path.join(dst_sub, fname)
                        if not os.path.exists(dst_file):
                            shutil.copyfile(os.path.join(src_sub, fname), dst_file)

            src_ref = os.path.join(tmp_dir, "refs", "heads", "main")
            if os.path.exists(src_ref):
                os.makedirs(os.path.join(mg, "refs", "heads"), exist_ok=True)
                shutil.copyfile(src_ref, os.path.join(mg, "refs", "heads", "main"))

            return self._send_json({"updated": name, "old_head": old_head, "new_head": new_head})
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="minigit_server — a tiny 'GitHub' for minigit repos")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--storage", default="storage", help="directory to store repos in")
    args = ap.parse_args()

    global STORAGE_DIR
    STORAGE_DIR = args.storage
    os.makedirs(STORAGE_DIR, exist_ok=True)

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"minigit-server listening on http://{args.host}:{args.port}  "
          f"(storage: {os.path.abspath(STORAGE_DIR)})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")


if __name__ == "__main__":
    main()
