#!/usr/bin/env python
"""
minigit — a tiny educational clone of core Git commands.

Implements:
    minigit init
    minigit add <file> [<file> ...]
    minigit commit -m "message"
    minigit clone <source_repo_path> <destination_path>
    minigit remote [<url>] [--create]
    minigit pull
    minigit push

Repository data lives in a hidden ".minigit" directory, structured
loosely like real Git:

    .minigit/
        objects/<sha1[:2]>/<sha1[2:]>   -> zlib-compressed blob/tree/commit objects
        refs/heads/main                 -> commit hash the branch points to
        HEAD                            -> "ref: refs/heads/main"
        index                           -> JSON: staged {path: blob_hash}
        config                          -> JSON: {"origin": "<path or URL used for clone/pull/push>"}

Remotes can be either:
  - another minigit repo on the local filesystem (a path), or
  - a minigit_server.py instance (an http:// or https:// URL, e.g.
    "http://localhost:8000/repos/demo")

This keeps the tool self-contained while still demonstrating the real
concepts: content-addressed storage, staging, commits with parents,
cloning, and fast-forward pulling/pushing.

Staging also respects:
  - MAX_FILE_SIZE: files larger than this are skipped with a warning.
  - .miniignore: gitignore-style ignore files. One may exist in any
    directory anywhere under the repo root; every pattern found in
    every .miniignore in the tree is applied globally. Patterns use
    shell-glob syntax (via fnmatch): "*" matches anything (ignores
    everything), "*.log" matches anything ending in ".log", "build*"
    matches anything starting with "build", etc. Blank lines and
    lines starting with "#" are ignored.
"""

import argparse
import fnmatch
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
import zlib

MINIGIT_DIR = ".minigit"
MINIIGNORE_FILE = ".miniignore"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# --------------------------------------------------------------------------
# Repository helpers
# --------------------------------------------------------------------------

def find_repo_root(start="."):
    """Walk upward from `start` looking for a .minigit directory."""
    path = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(path, MINIGIT_DIR)):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def minigit_path(root, *parts):
    return os.path.join(root, MINIGIT_DIR, *parts)


def read_index(root):
    idx_path = minigit_path(root, "index")
    if not os.path.exists(idx_path):
        return {}
    with open(idx_path, "r") as f:
        return json.load(f)


def write_index(root, index):
    with open(minigit_path(root, "index"), "w") as f:
        json.dump(index, f, indent=2)


def read_head_commit(root):
    """Return the commit hash HEAD points to, or None if there isn't one yet."""
    head_path = minigit_path(root, "HEAD")
    with open(head_path) as f:
        head = f.read().strip()
    if head.startswith("ref: "):
        ref_path = os.path.join(root, MINIGIT_DIR, head[5:])
        if not os.path.exists(ref_path):
            return None
        with open(ref_path) as f:
            return f.read().strip() or None
    return head or None


def write_head_commit(root, commit_hash):
    head_path = minigit_path(root, "HEAD")
    with open(head_path) as f:
        head = f.read().strip()
    if head.startswith("ref: "):
        ref_path = os.path.join(root, MINIGIT_DIR, head[5:])
        os.makedirs(os.path.dirname(ref_path), exist_ok=True)
        with open(ref_path, "w") as f:
            f.write(commit_hash + "\n")


def read_config(root):
    cfg_path = minigit_path(root, "config")
    if not os.path.exists(cfg_path):
        return {}
    with open(cfg_path) as f:
        return json.load(f)


def write_config(root, config):
    with open(minigit_path(root, "config"), "w") as f:
        json.dump(config, f, indent=2)


# --------------------------------------------------------------------------
# .miniignore handling
# --------------------------------------------------------------------------

def load_ignore_patterns(root):
    """
    Collect ignore patterns from every .miniignore file anywhere under
    `root` (the .minigit directory itself is always skipped). Patterns
    from all files are pooled into one flat, global list — a
    .miniignore can live in any directory in the project.
    """
    patterns = []
    for dirpath, dirnames, filenames in os.walk(root):
        # never descend into the repo's own internal storage
        if MINIGIT_DIR in dirnames:
            dirnames.remove(MINIGIT_DIR)
        if MINIIGNORE_FILE in filenames:
            ignore_file = os.path.join(dirpath, MINIIGNORE_FILE)
            with open(ignore_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    patterns.append(line.rstrip("/"))
    return patterns


def is_ignored(repo_rel_path, patterns):
    """
    Check a repo-relative path (forward-slash separated) against every
    pattern. A pattern matches (via fnmatch, so "*" = everything,
    "*foo" = anything ending in "foo", "foo*" = anything starting
    with "foo", etc.) if it matches:
      - the full repo-relative path,
      - the file's basename, or
      - any individual path segment (directory or file name) --
        this is what lets a plain directory name like "node_modules"
        (no wildcard) ignore everything nested inside that directory,
        not just a path that equals "node_modules" exactly.
    """
    if not patterns:
        return False
    segments = repo_rel_path.split("/")
    for pattern in patterns:
        if fnmatch.fnmatch(repo_rel_path, pattern):
            return True
        for segment in segments:
            if fnmatch.fnmatch(segment, pattern):
                return True
    return False


# --------------------------------------------------------------------------
# Object storage (content-addressed, like Git's blob/tree/commit objects)
# --------------------------------------------------------------------------

def hash_object(root, obj_type, data: bytes, write=True):
    header = f"{obj_type} {len(data)}\0".encode()
    full = header + data
    sha1 = hashlib.sha1(full).hexdigest()
    if write:
        obj_dir = minigit_path(root, "objects", sha1[:2])
        obj_file = os.path.join(obj_dir, sha1[2:])
        if not os.path.exists(obj_file):
            os.makedirs(obj_dir, exist_ok=True)
            with open(obj_file, "wb") as f:
                f.write(zlib.compress(full))
    return sha1


def read_object(root, sha1):
    obj_file = minigit_path(root, "objects", sha1[:2], sha1[2:])
    with open(obj_file, "rb") as f:
        full = zlib.decompress(f.read())
    header, data = full.split(b"\0", 1)
    obj_type, _size = header.decode().split(" ")
    return obj_type, data


def object_exists(root, sha1):
    return os.path.exists(minigit_path(root, "objects", sha1[:2], sha1[2:]))


# --------------------------------------------------------------------------
# HTTP remote helpers (talk to minigit_server.py)
# --------------------------------------------------------------------------

def is_url(s):
    return isinstance(s, str) and (s.startswith("http://") or s.startswith("https://"))


def zip_dir_bytes(path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _dirs, files in os.walk(path):
            for name in files:
                full = os.path.join(dirpath, name)
                arcname = os.path.relpath(full, path)
                zf.write(full, arcname)
    return buf.getvalue()


def download_repo_to_temp(url):
    """
    Download a remote .minigit archive from a minigit_server URL and extract
    it into a fresh temp directory laid out like a normal repo root (i.e.
    <tmp_root>/.minigit/...), so the rest of this file's helpers (read_object,
    read_head_commit, checkout_commit, ...) can treat it just like any other
    local repo.

    Caller is responsible for shutil.rmtree()-ing the returned path when done.
    """
    try:
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
    except urllib.error.URLError as e:
        sys.exit(f"fatal: could not reach '{url}': {e}")

    tmp_root = tempfile.mkdtemp(prefix="minigit-remote-")
    mg = os.path.join(tmp_root, MINIGIT_DIR)
    os.makedirs(mg, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(mg)
    return tmp_root


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_init(args):
    root = os.path.abspath(args.path)
    mg = os.path.join(root, MINIGIT_DIR)
    if os.path.isdir(mg):
        print(f"Reinitialized existing minigit repository in {mg}")
        return
    os.makedirs(os.path.join(mg, "objects"), exist_ok=True)
    os.makedirs(os.path.join(mg, "refs", "heads"), exist_ok=True)
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(mg, "HEAD"), "w") as f:
        f.write("ref: refs/heads/main\n")
    write_index(root, {})
    write_config(root, {})
    print(f"Initialized empty minigit repository in {mg}")


def _iter_all_repo_files(root):
    """
    Walk the entire repo tree (recursively, hierarchically) yielding every
    regular file's absolute path, skipping the .minigit internals dir.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        if MINIGIT_DIR in dirnames:
            dirnames.remove(MINIGIT_DIR)
        for name in filenames:
            yield os.path.join(dirpath, name)


def _stage_file(root, abs_path, index, added, skipped_size, skipped_ignored, patterns):
    """Stage a single file into `index`, respecting size limit and .miniignore."""
    repo_rel = os.path.relpath(abs_path, root).replace(os.sep, "/")

    if is_ignored(repo_rel, patterns):
        skipped_ignored.append(repo_rel)
        return

    size = os.path.getsize(abs_path)
    if size > MAX_FILE_SIZE:
        skipped_size.append((repo_rel, size))
        return

    with open(abs_path, "rb") as f:
        data = f.read()
    blob_hash = hash_object(root, "blob", data)
    index[repo_rel] = blob_hash
    added.append(repo_rel)


def cmd_add(args):
    root = find_repo_root()
    if root is None:
        sys.exit("fatal: not a minigit repository (or any parent up to root)")

    index = read_index(root)
    patterns = load_ignore_patterns(root)
    added = []
    skipped_size = []
    skipped_ignored = []

    # "minigit add ." or "minigit add" with no args - stage every file in
    # the repo, walking all subdirectories (not just the current directory).
    if not args.files or (len(args.files) == 1 and args.files[0] == "."):
        for abs_path in _iter_all_repo_files(root):
            _stage_file(root, abs_path, index, added, skipped_size, skipped_ignored, patterns)
    else:
        # Files (or directories) specified explicitly.
        for rel_path in args.files:
            abs_path = os.path.abspath(rel_path)
            if os.path.isdir(abs_path):
                for sub_abs_path in _iter_all_repo_files(abs_path):
                    _stage_file(root, sub_abs_path, index, added, skipped_size, skipped_ignored, patterns)
            elif os.path.isfile(abs_path):
                _stage_file(root, abs_path, index, added, skipped_size, skipped_ignored, patterns)
            else:
                print(f"warning: '{rel_path}' does not exist or is not a file, skipping")

    write_index(root, index)

    if added:
        print("Staged:")
        for path in added:
            print(f"  {path}")
    else:
        print("Nothing added.")

    for path, size in skipped_size:
        print(f"warning: '{path}' ({size} bytes) exceeds the {MAX_FILE_SIZE} byte limit, skipping")

    if skipped_ignored:
        print(f"Ignored {len(skipped_ignored)} file(s) per .miniignore")


def build_tree(root, index):
    """A minigit 'tree' is just a sorted, flat manifest of path -> blob hash."""
    entries = [{"path": p, "blob": h} for p, h in sorted(index.items())]
    data = json.dumps(entries).encode()
    return hash_object(root, "tree", data)


def cmd_commit(args):
    root = find_repo_root()
    if root is None:
        sys.exit("fatal: not a minigit repository (or any parent up to root)")

    index = read_index(root)
    if not index:
        sys.exit("nothing to commit (use 'minigit add' first)")

    tree_hash = build_tree(root, index)
    parent = read_head_commit(root)

    commit_data = {
        "tree": tree_hash,
        "parent": parent,
        "message": args.message,
        "author": args.author or os.environ.get("USER", "unknown"),
        "timestamp": time.time(),
    }
    commit_bytes = json.dumps(commit_data).encode()
    commit_hash = hash_object(root, "commit", commit_bytes)
    write_head_commit(root, commit_hash)

    short = commit_hash[:7]
    root_note = " (root-commit)" if parent is None else ""
    print(f"[main{root_note} {short}] {args.message}")
    print(f" {len(index)} file(s) committed")


def checkout_commit(root, commit_hash):
    """Write out every file from the given commit's tree into the working dir."""
    if commit_hash is None:
        return
    _, commit_bytes = read_object(root, commit_hash)
    commit_data = json.loads(commit_bytes)
    _, tree_bytes = read_object(root, commit_data["tree"])
    entries = json.loads(tree_bytes)
    for entry in entries:
        _, blob_data = read_object(root, entry["blob"])
        out_path = os.path.join(root, entry["path"])
        os.makedirs(os.path.dirname(out_path) or root, exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(blob_data)


def cmd_clone(args):
    dest = os.path.abspath(args.destination)
    if os.path.exists(dest) and os.listdir(dest):
        sys.exit(f"fatal: destination path '{args.destination}' already exists and is not empty")

    print(f"Cloning into '{args.destination}'...")
    os.makedirs(dest, exist_ok=True)

    if is_url(args.source):
        tmp_root = download_repo_to_temp(args.source)
        try:
            shutil.copytree(minigit_path(tmp_root), os.path.join(dest, MINIGIT_DIR))
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)
        write_config(dest, {"origin": args.source})
    else:
        src = os.path.abspath(args.source)
        src_mg = os.path.join(src, MINIGIT_DIR)
        if not os.path.isdir(src_mg):
            sys.exit(f"fatal: '{args.source}' is not a minigit repository")
        shutil.copytree(src_mg, os.path.join(dest, MINIGIT_DIR))
        write_config(dest, {"origin": src})

    head_commit = read_head_commit(dest)
    checkout_commit(dest, head_commit)

    if head_commit:
        print(f"done. checked out {head_commit[:7]}")
    else:
        print("done. (empty repository)")


def _create_remote_repo(url):
    """
    Send the PUT /repos/<name> request a minigit_server needs to create a
    brand-new, empty repo. Used by `minigit remote --create` so connecting
    a local folder to a fresh server-side repo doesn't require a manual
    curl call. A 409 (already exists) is treated as fine, not an error.
    """
    put_url = url.rstrip("/")
    if put_url.endswith("/archive"):
        put_url = put_url[: -len("/archive")]

    req = urllib.request.Request(put_url, method="PUT")
    try:
        with urllib.request.urlopen(req):
            print(f"Created empty repo on server at {put_url}")
    except urllib.error.HTTPError as e:
        if e.code == 409:
            print("Remote repo already exists on server, using it as-is.")
        else:
            body = e.read().decode(errors="replace")
            sys.exit(f"fatal: could not create remote repo ({e.code}): {body}")
    except urllib.error.URLError as e:
        sys.exit(f"fatal: could not reach '{put_url}': {e}")


def cmd_remote(args):
    """
    Show or set this repo's origin (the same "origin" field clone/pull/push
    read from .minigit/config). This is what lets an already-`init`-ed local
    folder connect to a remote without going through `clone`:

        minigit init
        minigit add .
        minigit commit -m "first commit"
        minigit remote http://localhost:8000/repos/demo --create
        minigit push
    """
    root = find_repo_root()
    if root is None:
        sys.exit("fatal: not a minigit repository (or any parent up to root)")

    config = read_config(root)

    if args.url is None:
        origin = config.get("origin")
        print(origin if origin else "No origin configured.")
        return

    if args.create:
        if not is_url(args.url):
            sys.exit("fatal: --create only works with an http(s):// minigit_server URL")
        _create_remote_repo(args.url)

    config["origin"] = args.url
    write_config(root, config)
    print(f"Set origin to {args.url}")


def _fast_forward_from(origin_root, root, remote_head, local_head):
    """
    Shared by cmd_pull for both local-path and downloaded-http origins:
    walk the remote commit chain (stored under origin_root), copy any
    objects `root` doesn't already have, and confirm the pull is a
    fast-forward. Returns (chain, copied_objects).
    """
    chain = []
    cursor = remote_head
    is_ff = local_head is None
    while cursor is not None:
        chain.append(cursor)
        if cursor == local_head:
            is_ff = True
            break
        _, commit_bytes = read_object(origin_root, cursor)
        cursor = json.loads(commit_bytes)["parent"]

    if not is_ff:
        sys.exit(
            "fatal: local history has diverged from origin; "
            "this minimal minigit only supports fast-forward pulls"
        )

    copied_objects = 0
    for commit_hash in chain:
        _, commit_bytes = read_object(origin_root, commit_hash)
        if not object_exists(root, commit_hash):
            hash_object(root, "commit", commit_bytes)
            copied_objects += 1
        commit_data = json.loads(commit_bytes)

        _, tree_bytes = read_object(origin_root, commit_data["tree"])
        if not object_exists(root, commit_data["tree"]):
            hash_object(root, "tree", tree_bytes)
            copied_objects += 1

        for entry in json.loads(tree_bytes):
            if not object_exists(root, entry["blob"]):
                _, blob_bytes = read_object(origin_root, entry["blob"])
                hash_object(root, "blob", blob_bytes)
                copied_objects += 1

    return chain, copied_objects


def cmd_pull(args):
    root = find_repo_root()
    if root is None:
        sys.exit("fatal: not a minigit repository (or any parent up to root)")

    config = read_config(root)
    origin = args.remote or config.get("origin")
    if not origin:
        sys.exit("fatal: no origin configured; run 'minigit clone' first or pass a remote")

    tmp_root = None
    if is_url(origin):
        tmp_root = download_repo_to_temp(origin)
        origin_root = tmp_root
    else:
        origin_root = os.path.abspath(origin)
        if not os.path.isdir(minigit_path(origin_root)):
            sys.exit(f"fatal: '{origin}' is not a minigit repository")

    try:
        remote_head = read_head_commit(origin_root)
        local_head = read_head_commit(root)

        if remote_head is None:
            print("Already up to date. (remote has no commits)")
            return
        if remote_head == local_head:
            print("Already up to date.")
            return

        chain, copied_objects = _fast_forward_from(origin_root, root, remote_head, local_head)

        write_head_commit(root, remote_head)
        checkout_commit(root, remote_head)

        new_commits = len(chain) - (1 if local_head in chain else 0)
        print(f"Updating {(local_head or '0000000')[:7]}..{remote_head[:7]}")
        print(f"Fast-forward: {new_commits} new commit(s), {copied_objects} object(s) fetched")
    finally:
        if tmp_root:
            shutil.rmtree(tmp_root, ignore_errors=True)


def cmd_push(args):
    root = find_repo_root()
    if root is None:
        sys.exit("fatal: not a minigit repository (or any parent up to root)")

    config = read_config(root)
    origin = args.remote or config.get("origin")
    if not origin:
        sys.exit("fatal: no origin configured; run 'minigit clone' first or pass a remote")
    if not is_url(origin):
        sys.exit(
            "fatal: push only supports http(s) origins (a minigit_server.py remote). "
            "For a local-path remote, run 'pull' from the other side instead."
        )

    local_head = read_head_commit(root)
    if local_head is None:
        sys.exit("fatal: nothing to push (no commits yet)")

    push_url = origin.rstrip("/")
    if push_url.endswith("/archive"):
        push_url = push_url[: -len("/archive")]
    push_url += "/push"
    if args.force:
        push_url += "?force=1"

    data = zip_dir_bytes(minigit_path(root))
    req = urllib.request.Request(push_url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            body = json.loads(body).get("error", body)
        except (json.JSONDecodeError, AttributeError):
            pass
        sys.exit(f"fatal: push rejected ({e.code}): {body}")
    except urllib.error.URLError as e:
        sys.exit(f"fatal: could not reach '{origin}': {e}")

    old_head = result.get("old_head")
    print(f"Pushed to {origin}")
    print(f"  {(old_head or '0000000')[:7]}..{result.get('new_head', '')[:7]}")


def cmd_log(args):
    """Small bonus command — handy for sanity-checking the other commands."""
    root = find_repo_root()
    if root is None:
        sys.exit("fatal: not a minigit repository (or any parent up to root)")
    cursor = read_head_commit(root)
    if cursor is None:
        print("No commits yet.")
        return
    while cursor is not None:
        _, commit_bytes = read_object(root, cursor)
        data = json.loads(commit_bytes)
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data["timestamp"]))
        print(f"commit {cursor}")
        print(f"Author: {data['author']}")
        print(f"Date:   {ts}")
        print(f"\n    {data['message']}\n")
        cursor = data["parent"]


# --------------------------------------------------------------------------
# CLI wiring
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(prog="minigit", description="A tiny educational Git clone.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create an empty minigit repository")
    p_init.add_argument("path", nargs="?", default=".", help="where to create the repo")
    p_init.set_defaults(func=cmd_init)

    p_add = sub.add_parser("add", help="stage file(s) for the next commit")
    p_add.add_argument("files", nargs="*", help="file(s)/dir(s) to stage (use '.' to stage all, recursively)")
    p_add.set_defaults(func=cmd_add)

    p_commit = sub.add_parser("commit", help="record staged changes")
    p_commit.add_argument("-m", "--message", required=True, help="commit message")
    p_commit.add_argument("--author", help="override author name")
    p_commit.set_defaults(func=cmd_commit)

    p_clone = sub.add_parser("clone", help="clone a repository into a new directory")
    p_clone.add_argument("source", help="path to a local minigit repo, or an http(s):// URL "
                                         "to a repo hosted by minigit_server.py")
    p_clone.add_argument("destination", help="path to create the clone in")
    p_clone.set_defaults(func=cmd_clone)

    p_remote = sub.add_parser("remote", help="show or set the repo's origin (path or minigit_server URL)")
    p_remote.add_argument("url", nargs="?", help="origin to set; omit to show the current origin")
    p_remote.add_argument("--create", action="store_true",
                           help="also create the repo on the server if it doesn't exist yet "
                                "(http(s) origins only)")
    p_remote.set_defaults(func=cmd_remote)

    p_pull = sub.add_parser("pull", help="fast-forward from the configured origin")
    p_pull.add_argument("remote", nargs="?", help="override the configured origin (path or URL)")
    p_pull.set_defaults(func=cmd_pull)

    p_push = sub.add_parser("push", help="push local commits to an http(s) origin")
    p_push.add_argument("remote", nargs="?", help="override the configured origin (must be a URL)")
    p_push.add_argument("--force", action="store_true",
                         help="skip the server's fast-forward check")
    p_push.set_defaults(func=cmd_push)

    p_log = sub.add_parser("log", help="show commit history (bonus command)")
    p_log.set_defaults(func=cmd_log)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
