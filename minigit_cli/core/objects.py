import hashlib
import zlib
import os
import time

def hash_object(data: bytes, obj_type: str = "blob", write: bool = False, repo_path: str = None) -> str:
    """
    Computes SHA-1 hash of header + data: '<type> <size>\0<data>'
    Optionally writes zlib-compressed object into .minigit/objects/xx/yyyy...
    """
    header = f"{obj_type} {len(data)}\x00".encode('utf-8')
    full_payload = header + data
    sha1 = hashlib.sha1(full_payload).hexdigest()

    if write and repo_path:
        obj_dir = os.path.join(repo_path, ".minigit", "objects", sha1[:2])
        obj_file = os.path.join(obj_dir, sha1[2:])
        if not os.path.exists(obj_file):
            os.makedirs(obj_dir, exist_ok=True)
            compressed = zlib.compress(full_payload)
            with open(obj_file, "wb") as f:
                f.write(compressed)

    return sha1

def read_object(sha1: str, repo_path: str) -> tuple[str, bytes]:
    """
    Reads object from .minigit/objects/xx/yyyy...
    Returns (obj_type, content_bytes)
    """
    obj_file = os.path.join(repo_path, ".minigit", "objects", sha1[:2], sha1[2:])
    if not os.path.isfile(obj_file):
        raise FileNotFoundError(f"Object {sha1} not found in repository.")

    with open(obj_file, "rb") as f:
        compressed = f.read()

    decompressed = zlib.decompress(compressed)
    null_idx = decompressed.find(b"\x00")
    if null_idx == -1:
        raise ValueError(f"Corrupted object header for {sha1}")

    header = decompressed[:null_idx].decode('utf-8')
    content = decompressed[null_idx + 1:]
    obj_type, _ = header.split(" ", 1)
    return obj_type, content

def create_tree_from_index(index: dict, repo_path: str) -> str:
    """
    Builds a tree object from staged files index dictionary:
    { "relative/file/path": { "hash": sha, "mode": "100644" } }
    Returns tree SHA-1.
    """
    # Group files by top-level directories
    directories = {}
    files = {}

    for path, info in index.items():
        parts = path.split('/', 1)
        if len(parts) == 1:
            files[parts[0]] = info
        else:
            dir_name, rest = parts[0], parts[1]
            if dir_name not in directories:
                directories[dir_name] = {}
            directories[dir_name][rest] = info

    entries = []

    # Process files
    for filename, info in sorted(files.items()):
        mode = info.get('mode', '100644')
        sha = info['hash']
        entries.append(f"{mode} blob {sha}\t{filename}".encode('utf-8'))

    # Process subdirectories recursively
    for dir_name, sub_index in sorted(directories.items()):
        sub_tree_sha = create_tree_from_index(sub_index, repo_path)
        entries.append(f"040000 tree {sub_tree_sha}\t{dir_name}".encode('utf-8'))

    tree_data = b"\n".join(entries)
    return hash_object(tree_data, obj_type="tree", write=True, repo_path=repo_path)

def create_commit(tree_sha: str, parent_sha: str | None, message: str, author: str, repo_path: str) -> str:
    """
    Creates a commit object and writes it into object store.
    """
    timestamp = int(time.time())
    lines = [
        f"tree {tree_sha}",
    ]
    if parent_sha:
        lines.append(f"parent {parent_sha}")
    lines.append(f"author {author} {timestamp} +0000")
    lines.append(f"committer {author} {timestamp} +0000")
    lines.append("")
    lines.append(message)

    commit_data = "\n".join(lines).encode('utf-8')
    return hash_object(commit_data, obj_type="commit", write=True, repo_path=repo_path)

def parse_commit(content_bytes: bytes) -> dict:
    """
    Parses commit payload text into structured dict.
    """
    text = content_bytes.decode('utf-8', errors='replace')
    lines = text.split("\n")
    headers = {}
    msg_lines = []
    in_msg = False

    for line in lines:
        if in_msg:
            msg_lines.append(line)
        elif line == "":
            in_msg = True
        else:
            parts = line.split(" ", 1)
            if len(parts) == 2:
                key, val = parts
                if key in headers:
                    if isinstance(headers[key], list):
                        headers[key].append(val)
                    else:
                        headers[key] = [headers[key], val]
                else:
                    headers[key] = val

    headers['message'] = "\n".join(msg_lines).strip()
    return headers
