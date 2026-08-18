import os
import zlib
from ..core.objects import read_object, hash_object

def collect_objects_for_commit(commit_sha: str, repo_path: str, visited: set | None = None) -> list[dict]:
    """
    Traverses commit tree and parents to collect all reachable git objects
    (commit, trees, blobs) for push transport.
    """
    if visited is None:
        visited = set()

    if commit_sha in visited:
        return []

    objects = []
    try:
        obj_type, data = read_object(commit_sha, repo_path)
    except FileNotFoundError:
        return []

    visited.add(commit_sha)
    objects.append({
        "sha": commit_sha,
        "type": obj_type,
        "content_hex": data.hex()
    })

    if obj_type == "commit":
        text = data.decode('utf-8', errors='replace')
        lines = text.split("\n")
        tree_sha = None
        parents = []
        for line in lines:
            if line.startswith("tree "):
                tree_sha = line[5:].strip()
            elif line.startswith("parent "):
                parents.append(line[7:].strip())

        if tree_sha:
            objects.extend(collect_objects_for_commit(tree_sha, repo_path, visited))
        for p_sha in parents:
            objects.extend(collect_objects_for_commit(p_sha, repo_path, visited))

    elif obj_type == "tree":
        text = data.decode('utf-8', errors='replace')
        lines = text.split("\n")
        for line in lines:
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                meta = parts[0].split(" ")
                if len(meta) == 3:
                    item_type, item_sha = meta[1], meta[2]
                    if item_sha not in visited:
                        objects.extend(collect_objects_for_commit(item_sha, repo_path, visited))

    return objects

def write_objects_to_repo(objects: list[dict], repo_path: str):
    """
    Writes array of object dicts {"sha": ..., "type": ..., "content_hex": ...} into local repo.
    """
    for obj in objects:
        content = bytes.fromhex(obj["content_hex"])
        hash_object(content, obj_type=obj["type"], write=True, repo_path=repo_path)
