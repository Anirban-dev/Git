import os
import json
import hashlib
from .objects import hash_object, read_object, parse_commit
from .ignore import IgnoreMatcher

def find_repo_root(start_path: str = ".") -> str | None:
    """
    Recursively searches upwards for .minigit directory.
    """
    current = os.path.abspath(start_path)
    while True:
        if os.path.isdir(os.path.join(current, ".minigit")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None

def init_repository(repo_path: str) -> str:
    """
    Initializes a new .minigit repository directory structure.
    """
    abs_path = os.path.abspath(repo_path)
    minigit_dir = os.path.join(abs_path, ".minigit")

    os.makedirs(os.path.join(minigit_dir, "objects"), exist_ok=True)
    os.makedirs(os.path.join(minigit_dir, "refs", "heads"), exist_ok=True)

    # Default HEAD points to refs/heads/main
    head_file = os.path.join(minigit_dir, "HEAD")
    if not os.path.isfile(head_file):
        with open(head_file, "w", encoding="utf-8") as f:
            f.write("ref: refs/heads/main\n")

    # Empty index
    index_file = os.path.join(minigit_dir, "index")
    if not os.path.isfile(index_file):
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump({}, f)

    return abs_path

def get_current_branch_or_commit(repo_path: str) -> tuple[str, str | None]:
    """
    Returns (branch_name_or_sha, current_commit_sha)
    """
    head_file = os.path.join(repo_path, ".minigit", "HEAD")
    if not os.path.isfile(head_file):
        return ("main", None)

    with open(head_file, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if content.startswith("ref: "):
        ref_path = content[5:]
        branch_name = ref_path.replace("refs/heads/", "")
        ref_full_file = os.path.join(repo_path, ".minigit", ref_path)
        commit_sha = None
        if os.path.isfile(ref_full_file):
            with open(ref_full_file, "r", encoding="utf-8") as rf:
                commit_sha = rf.read().strip()
        return (branch_name, commit_sha)
    else:
        # Detached HEAD
        return (f"detached at {content[:7]}", content)

def set_branch_commit(repo_path: str, branch: str, commit_sha: str):
    ref_file = os.path.join(repo_path, ".minigit", "refs", "heads", branch)
    os.makedirs(os.path.dirname(ref_file), exist_ok=True)
    with open(ref_file, "w", encoding="utf-8") as f:
        f.write(commit_sha + "\n")

def read_index(repo_path: str) -> dict:
    index_file = os.path.join(repo_path, ".minigit", "index")
    if os.path.isfile(index_file):
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def write_index(repo_path: str, index_data: dict):
    index_file = os.path.join(repo_path, ".minigit", "index")
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2)

def extract_tree_files(tree_sha: str, repo_path: str, prefix: str = "") -> dict:
    """
    Recursively extracts all files from a tree object into a flat dict:
    { "file/path": "blob_sha" }
    """
    result = {}
    obj_type, data = read_object(tree_sha, repo_path)
    if obj_type != "tree":
        return result

    lines = data.decode('utf-8', errors='replace').split("\n")
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            meta, name = parts
            meta_parts = meta.split(" ")
            if len(meta_parts) == 3:
                mode, otype, sha = meta_parts
                rel_path = f"{prefix}/{name}" if prefix else name
                if otype == "blob":
                    result[rel_path] = sha
                elif otype == "tree":
                    sub_files = extract_tree_files(sha, repo_path, prefix=rel_path)
                    result.update(sub_files)
    return result

def get_status(repo_path: str) -> dict:
    """
    Computes staged, unstaged modified, untracked, and deleted files.
    """
    index = read_index(repo_path)
    branch, commit_sha = get_current_branch_or_commit(repo_path)

    head_files = {}
    if commit_sha:
        try:
            obj_type, commit_data = read_object(commit_sha, repo_path)
            commit = parse_commit(commit_data)
            if 'tree' in commit:
                head_files = extract_tree_files(commit['tree'], repo_path)
        except Exception:
            pass

    matcher = IgnoreMatcher(repo_path)

    working_files = {}
    for root, dirs, files in os.walk(repo_path):
        rel_dir = os.path.relpath(root, repo_path)
        if rel_dir == ".":
            rel_dir = ""

        # Filter out ignored directories
        dirs[:] = [d for d in dirs if not matcher.is_ignored(os.path.join(rel_dir, d))]

        for file in files:
            rel_file = os.path.join(rel_dir, file).replace("\\", "/")
            if matcher.is_ignored(rel_file):
                continue

            full_file = os.path.join(root, file)
            try:
                with open(full_file, "rb") as f:
                    content = f.read()
                file_hash = hash_object(content, obj_type="blob", write=False)
                working_files[rel_file] = file_hash
            except Exception:
                pass

    staged = []
    unstaged_modified = []
    untracked = []
    deleted = []

    # Check staged vs HEAD
    for path, info in index.items():
        staged_hash = info['hash']
        head_hash = head_files.get(path)
        if staged_hash != head_hash:
            staged.append(path)

        # Check working directory vs staged
        if path in working_files:
            if working_files[path] != staged_hash:
                unstaged_modified.append(path)
        else:
            deleted.append(path)

    # Check untracked
    for path in working_files:
        if path not in index:
            untracked.append(path)

    return {
        "branch": branch,
        "commit": commit_sha,
        "staged": sorted(staged),
        "modified": sorted(unstaged_modified),
        "untracked": sorted(untracked),
        "deleted": sorted(deleted)
    }
