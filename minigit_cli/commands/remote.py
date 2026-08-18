import sys
import os
from ..core.repository import (
    find_repo_root,
    init_repository,
    read_index,
    write_index,
    get_current_branch_or_commit,
    set_branch_commit,
    extract_tree_files
)
from ..core.objects import read_object, parse_commit
from ..core.config import (
    load_global_credentials,
    load_local_config,
    save_local_config
)
from ..remote.client import (
    create_remote_repo,
    push_to_remote,
    pull_from_remote
)
from ..remote.protocol import collect_objects_for_commit, write_objects_to_repo

DEFAULT_SERVER_URL = "http://localhost:3000"

def cmd_remote(args):
    repo_path = find_repo_root()
    if not repo_path:
        print("fatal: not a minigit repository")
        sys.exit(1)

    cfg = load_local_config(repo_path)
    sub = args.remote_cmd

    if not sub or sub == "list":
        remotes = cfg.get("remotes", {})
        for name, url in remotes.items():
            print(f"{name}\t{url} (fetch & push)")
    elif sub == "add":
        name = args.name
        url = args.url
        remotes = cfg.get("remotes", {})
        remotes[name] = url
        cfg["remotes"] = remotes
        save_local_config(repo_path, cfg)
        print(f"Remote '{name}' set to {url}")

        if getattr(args, "create", False):
            creds = load_global_credentials()
            server_url = creds.get("server", DEFAULT_SERVER_URL)
            repo_name = url.split("/")[-1]
            try:
                res = create_remote_repo(server_url, repo_name)
                print(f"Created remote repository '{res['repo']['owner']}/{res['repo']['name']}' on server.")
            except Exception as e:
                print(f"Note: Remote repo creation on server returned: {e}")

def cmd_push(args):
    repo_path = find_repo_root()
    if not repo_path:
        print("fatal: not a minigit repository")
        sys.exit(1)

    cfg = load_local_config(repo_path)
    remotes = cfg.get("remotes", {})
    remote_name = args.remote or "origin"
    remote_url = remotes.get(remote_name)

    if not remote_url:
        print(f"fatal: No remote '{remote_name}' configured. Use 'minigit remote add origin <url>'.")
        sys.exit(1)

    branch, commit_sha = get_current_branch_or_commit(repo_path)
    if not commit_sha:
        print("fatal: nothing to push (no commits yet)")
        sys.exit(1)

    objects = collect_objects_for_commit(commit_sha, repo_path)
    print(f"Compressing & pushing {len(objects)} object(s) to {remote_url}...")

    push_to_remote(remote_url, branch, commit_sha, objects)
    print(f"Pushed to {remote_url}")
    print(f"  Branch '{branch}' updated -> {commit_sha[:7]}")

def cmd_pull(args):
    repo_path = find_repo_root()
    if not repo_path:
        print("fatal: not a minigit repository")
        sys.exit(1)

    cfg = load_local_config(repo_path)
    remotes = cfg.get("remotes", {})
    remote_name = args.remote or "origin"
    remote_url = remotes.get(remote_name)

    if not remote_url:
        print(f"fatal: No remote '{remote_name}' configured.")
        sys.exit(1)

    branch, _ = get_current_branch_or_commit(repo_path)
    print(f"Fetching from {remote_url}...")
    res = pull_from_remote(remote_url, branch)

    objects = res.get("objects", [])
    write_objects_to_repo(objects, repo_path)

    remote_sha = res.get("head_commit")
    if remote_sha:
        set_branch_commit(repo_path, branch, remote_sha)
        _, data = read_object(remote_sha, repo_path)
        commit = parse_commit(data)
        if 'tree' in commit:
            tree_files = extract_tree_files(commit['tree'], repo_path)
            new_index = {}
            for rel_path, blob_sha in tree_files.items():
                _, blob_data = read_object(blob_sha, repo_path)
                full_file = os.path.join(repo_path, rel_path)
                os.makedirs(os.path.dirname(full_file), exist_ok=True)
                with open(full_file, "wb") as f:
                    f.write(blob_data)
                new_index[rel_path] = {"hash": blob_sha, "mode": "100644"}
            write_index(repo_path, new_index)

        print(f"Updated branch '{branch}' -> {remote_sha[:7]}")

def cmd_clone(args):
    remote_url = args.url
    target_dir = args.directory or remote_url.split("/")[-1].replace(".git", "")

    print(f"Cloning into '{target_dir}'...")
    os.makedirs(target_dir, exist_ok=True)
    repo_path = init_repository(target_dir)

    cfg = load_local_config(repo_path)
    cfg["remotes"] = {"origin": remote_url}
    save_local_config(repo_path, cfg)

    res = pull_from_remote(remote_url, "main")
    objects = res.get("objects", [])
    write_objects_to_repo(objects, repo_path)

    remote_sha = res.get("head_commit")
    if remote_sha:
        set_branch_commit(repo_path, "main", remote_sha)
        _, data = read_object(remote_sha, repo_path)
        commit = parse_commit(data)
        if 'tree' in commit:
            tree_files = extract_tree_files(commit['tree'], repo_path)
            new_index = {}
            for rel_path, blob_sha in tree_files.items():
                _, blob_data = read_object(blob_sha, repo_path)
                full_file = os.path.join(repo_path, rel_path)
                os.makedirs(os.path.dirname(full_file), exist_ok=True)
                with open(full_file, "wb") as f:
                    f.write(blob_data)
                new_index[rel_path] = {"hash": blob_sha, "mode": "100644"}
            write_index(repo_path, new_index)

    print(f"Clone complete in '{target_dir}'.")
