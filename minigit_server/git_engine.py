import os
import json
import zlib
import hashlib
import zipfile
import io
from .config import REPOS_DIR

def get_repo_path(owner: str, name: str) -> str:
    """
    Multi-account isolated storage path: storage/repos/<owner>/<name>
    """
    return os.path.join(REPOS_DIR, owner.lower(), name.lower())

def ensure_server_repo(owner: str, name: str) -> str:
    """
    Ensures .minigit repository directory structure exists on server.
    """
    repo_path = get_repo_path(owner, name)
    minigit_dir = os.path.join(repo_path, ".minigit")
    os.makedirs(os.path.join(minigit_dir, "objects"), exist_ok=True)
    os.makedirs(os.path.join(minigit_dir, "refs", "heads"), exist_ok=True)

    head_file = os.path.join(minigit_dir, "HEAD")
    if not os.path.isfile(head_file):
        with open(head_file, "w", encoding="utf-8") as f:
            f.write("ref: refs/heads/main\n")

    index_file = os.path.join(minigit_dir, "index")
    if not os.path.isfile(index_file):
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump({}, f)

    return repo_path

def store_raw_object(repo_path: str, sha1: str, obj_type: str, content: bytes):
    """
    Stores git object into .minigit/objects/xx/yyyy...
    """
    obj_dir = os.path.join(repo_path, ".minigit", "objects", sha1[:2])
    obj_file = os.path.join(obj_dir, sha1[2:])

    if not os.path.exists(obj_file):
        os.makedirs(obj_dir, exist_ok=True)
        header = f"{obj_type} {len(content)}\x00".encode('utf-8')
        full_payload = header + content
        compressed = zlib.compress(full_payload)
        with open(obj_file, "wb") as f:
            f.write(compressed)

def read_server_object(repo_path: str, sha1: str) -> tuple[str, bytes]:
    obj_file = os.path.join(repo_path, ".minigit", "objects", sha1[:2], sha1[2:])
    if not os.path.isfile(obj_file):
        raise FileNotFoundError(f"Object {sha1} not found")

    with open(obj_file, "rb") as f:
        compressed = f.read()

    decompressed = zlib.decompress(compressed)
    null_idx = decompressed.find(b"\x00")
    if null_idx == -1:
        raise ValueError("Corrupted object")

    header = decompressed[:null_idx].decode('utf-8')
    content = decompressed[null_idx + 1:]
    obj_type, _ = header.split(" ", 1)
    return obj_type, content

def update_repo_ref(repo_path: str, branch: str, commit_sha: str):
    ref_file = os.path.join(repo_path, ".minigit", "refs", "heads", branch)
    os.makedirs(os.path.dirname(ref_file), exist_ok=True)
    with open(ref_file, "w", encoding="utf-8") as f:
        f.write(commit_sha + "\n")

def get_repo_ref(repo_path: str, branch: str = "main") -> str | None:
    ref_file = os.path.join(repo_path, ".minigit", "refs", "heads", branch)
    if os.path.isfile(ref_file):
        with open(ref_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def collect_server_objects(repo_path: str, commit_sha: str, visited: set | None = None) -> list[dict]:
    if visited is None:
        visited = set()

    if commit_sha in visited:
        return []

    try:
        obj_type, data = read_server_object(repo_path, commit_sha)
    except FileNotFoundError:
        return []

    visited.add(commit_sha)
    result = [{
        "sha": commit_sha,
        "type": obj_type,
        "content_hex": data.hex()
    }]

    if obj_type == "commit":
        lines = data.decode('utf-8', errors='replace').split("\n")
        tree_sha = None
        parents = []
        for line in lines:
            if line.startswith("tree "):
                tree_sha = line[5:].strip()
            elif line.startswith("parent "):
                parents.append(line[7:].strip())

        if tree_sha:
            result.extend(collect_server_objects(repo_path, tree_sha, visited))
        for p in parents:
            result.extend(collect_server_objects(repo_path, p, visited))

    elif obj_type == "tree":
        lines = data.decode('utf-8', errors='replace').split("\n")
        for line in lines:
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                meta = parts[0].split(" ")
                if len(meta) == 3:
                    item_type, item_sha = meta[1], meta[2]
                    if item_sha not in visited:
                        result.extend(collect_server_objects(repo_path, item_sha, visited))

    return result

def create_zip_archive_bytes(repo_path: str, commit_sha: str) -> bytes:
    """
    Creates an in-memory zip archive of the files at commit_sha.
    """
    zip_buffer = io.BytesIO()

    def _extract_tree(tree_sha: str, prefix: str = "") -> dict:
        out = {}
        obj_type, data = read_server_object(repo_path, tree_sha)
        lines = data.decode('utf-8', errors='replace').split("\n")
        for line in lines:
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                meta, name = parts
                mparts = meta.split(" ")
                if len(mparts) == 3:
                    _, otype, sha = mparts
                    rel_p = f"{prefix}/{name}" if prefix else name
                    if otype == "blob":
                        out[rel_p] = sha
                    elif otype == "tree":
                        out.update(_extract_tree(sha, rel_p))
        return out

    obj_type, commit_data = read_server_object(repo_path, commit_sha)
    tree_sha = None
    for line in commit_data.decode('utf-8', errors='replace').split("\n"):
        if line.startswith("tree "):
            tree_sha = line[5:].strip()
            break

    files_map = _extract_tree(tree_sha) if tree_sha else {}

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, b_sha in files_map.items():
            _, b_data = read_server_object(repo_path, b_sha)
            zf.writestr(path, b_data)

    return zip_buffer.getvalue()
