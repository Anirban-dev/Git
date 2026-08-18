import sys
import os
import difflib
from ..core.repository import (
    find_repo_root,
    init_repository,
    get_status,
    read_index,
    write_index,
    get_current_branch_or_commit,
    set_branch_commit
)
from ..core.objects import (
    hash_object,
    create_tree_from_index,
    create_commit,
    read_object,
    parse_commit
)
from ..core.config import load_global_credentials

def cmd_init(args):
    repo_dir = args.directory or "."
    abs_path = init_repository(repo_dir)
    print(f"Initialized empty MiniGit repository in {os.path.join(abs_path, '.minigit')}")

def cmd_add(args):
    repo_path = find_repo_root()
    if not repo_path:
        print("fatal: not a minigit repository (or any of the parent directories)")
        sys.exit(1)

    index = read_index(repo_path)
    status = get_status(repo_path)

    targets = args.files
    added_count = 0

    if "." in targets or "all" in targets:
        to_add = status["modified"] + status["untracked"]
        for rel_file in to_add:
            full_path = os.path.join(repo_path, rel_file)
            if os.path.isfile(full_path):
                with open(full_path, "rb") as f:
                    content = f.read()
                sha = hash_object(content, obj_type="blob", write=True, repo_path=repo_path)
                index[rel_file] = {"hash": sha, "mode": "100644"}
                added_count += 1
    else:
        for target in targets:
            rel_target = os.path.relpath(os.path.abspath(target), repo_path).replace("\\", "/")
            full_path = os.path.join(repo_path, rel_target)
            if os.path.isfile(full_path):
                with open(full_path, "rb") as f:
                    content = f.read()
                sha = hash_object(content, obj_type="blob", write=True, repo_path=repo_path)
                index[rel_target] = {"hash": sha, "mode": "100644"}
                added_count += 1
            else:
                print(f"warning: pathspec '{target}' did not match any files")

    write_index(repo_path, index)
    print(f"Staged {added_count} file(s).")

def cmd_commit(args):
    repo_path = find_repo_root()
    if not repo_path:
        print("fatal: not a minigit repository")
        sys.exit(1)

    index = read_index(repo_path)
    if not index:
        print("nothing to commit (use 'minigit add' to track files)")
        sys.exit(1)

    branch, parent_sha = get_current_branch_or_commit(repo_path)
    creds = load_global_credentials()
    user_name = creds.get("user", {}).get("username") or os.environ.get("USER") or "developer"

    tree_sha = create_tree_from_index(index, repo_path)
    commit_sha = create_commit(tree_sha, parent_sha, args.message, user_name, repo_path)

    set_branch_commit(repo_path, branch, commit_sha)
    print(f"[{branch} (root-commit {commit_sha[:7]})] {args.message}")
    print(f" {len(index)} file(s) changed")

def cmd_status(args):
    repo_path = find_repo_root()
    if not repo_path:
        print("fatal: not a minigit repository")
        sys.exit(1)

    st = get_status(repo_path)
    print(f"On branch {st['branch']}")
    if not st['commit']:
        print("\nNo commits yet")

    if st['staged']:
        print("\nChanges to be committed:")
        for f in st['staged']:
            print(f"  \033[32mnew file/modified: {f}\033[0m")

    if st['modified']:
        print("\nChanges not staged for commit:")
        for f in st['modified']:
            print(f"  \033[31mmodified:   {f}\033[0m")

    if st['untracked']:
        print("\nUntracked files:")
        for f in st['untracked']:
            print(f"  \033[31m{f}\033[0m")

    if not st['staged'] and not st['modified'] and not st['untracked']:
        print("nothing to commit, working tree clean")

def cmd_log(args):
    repo_path = find_repo_root()
    if not repo_path:
        print("fatal: not a minigit repository")
        sys.exit(1)

    branch, commit_sha = get_current_branch_or_commit(repo_path)
    if not commit_sha:
        print(f"On branch {branch}\nNo commits yet.")
        return

    curr = commit_sha
    while curr:
        try:
            _, data = read_object(curr, repo_path)
            c = parse_commit(data)
            print(f"\033[33mcommit {curr}\033[0m")
            print(f"Author: {c.get('author', 'Unknown')}")
            print(f"\n    {c.get('message', '')}\n")

            parent = c.get('parent')
            if isinstance(parent, list):
                curr = parent[0]
            else:
                curr = parent
        except Exception:
            break

def cmd_diff(args):
    repo_path = find_repo_root()
    if not repo_path:
        print("fatal: not a minigit repository")
        sys.exit(1)

    st = get_status(repo_path)
    index = read_index(repo_path)

    for rel_file in st['modified']:
        staged_info = index.get(rel_file)
        if not staged_info:
            continue
        try:
            _, staged_bytes = read_object(staged_info['hash'], repo_path)
            staged_lines = staged_bytes.decode('utf-8', errors='replace').splitlines()

            full_file = os.path.join(repo_path, rel_file)
            with open(full_file, "r", encoding="utf-8", errors="replace") as f:
                working_lines = f.read().splitlines()

            print(f"--- a/{rel_file}")
            print(f"+++ b/{rel_file}")
            diff = difflib.unified_diff(staged_lines, working_lines, fromfile=f"a/{rel_file}", tofile=f"b/{rel_file}")
            for line in diff:
                if line.startswith("+"):
                    print(f"\033[32m{line}\033[0m")
                elif line.startswith("-"):
                    print(f"\033[31m{line}\033[0m")
                else:
                    print(line)
        except Exception as e:
            print(f"Could not diff {rel_file}: {e}")
