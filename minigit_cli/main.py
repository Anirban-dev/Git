import sys
import argparse
from .commands.auth import cmd_auth
from .commands.local import (
    cmd_init,
    cmd_add,
    cmd_commit,
    cmd_status,
    cmd_log,
    cmd_diff
)
from .commands.remote import (
    cmd_remote,
    cmd_push,
    cmd_pull,
    cmd_clone
)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="minigit", description="MiniGit Version Control System")
    subparsers = parser.add_subparsers(dest="command")

    # Auth
    p_auth = subparsers.add_parser("auth", help="User authentication management")
    p_auth.add_argument("--server", help="Server URL (default: http://localhost:3000)")
    auth_sub = p_auth.add_subparsers(dest="auth_cmd")
    auth_sub.add_parser("register", help="Register a new user account")
    auth_sub.add_parser("login", help="Log in to account")
    auth_sub.add_parser("logout", help="Log out")
    auth_sub.add_parser("status", help="Show authentication status")
    auth_sub.add_parser("token", help="Generate Personal Access Token")

    # Local repository commands
    p_init = subparsers.add_parser("init", help="Initialize a new repository")
    p_init.add_argument("directory", nargs="?", default=".", help="Directory path")

    p_add = subparsers.add_parser("add", help="Add file contents to the index")
    p_add.add_argument("files", nargs="+", help="Files or '.' to add")

    p_commit = subparsers.add_parser("commit", help="Record changes to the repository")
    p_commit.add_argument("-m", "--message", required=True, help="Commit message")

    subparsers.add_parser("status", help="Show working tree status")
    subparsers.add_parser("log", help="Show commit logs")
    subparsers.add_parser("diff", help="Show changes between commits/working tree")

    # Remote commands
    p_remote = subparsers.add_parser("remote", help="Manage set of tracked repositories")
    remote_sub = p_remote.add_subparsers(dest="remote_cmd")
    p_rem_add = remote_sub.add_parser("add", help="Add remote repository")
    p_rem_add.add_argument("name", help="Remote name (e.g. origin)")
    p_rem_add.add_argument("url", help="Remote repository URL")
    p_rem_add.add_argument("--create", action="store_true", help="Auto-create remote repository on server")

    p_push = subparsers.add_parser("push", help="Update remote refs along with associated objects")
    p_push.add_argument("remote", nargs="?", default="origin", help="Remote name")
    p_push.add_argument("branch", nargs="?", default="main", help="Branch name")

    p_pull = subparsers.add_parser("pull", help="Fetch from and integrate with another repository")
    p_pull.add_argument("remote", nargs="?", default="origin", help="Remote name")

    p_clone = subparsers.add_parser("clone", help="Clone a repository into a new directory")
    p_clone.add_argument("url", help="Repository URL to clone")
    p_clone.add_argument("directory", nargs="?", help="Target directory")

    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    handlers = {
        "auth": cmd_auth,
        "init": cmd_init,
        "add": cmd_add,
        "commit": cmd_commit,
        "status": cmd_status,
        "log": cmd_log,
        "diff": cmd_diff,
        "remote": cmd_remote,
        "push": cmd_push,
        "pull": cmd_pull,
        "clone": cmd_clone,
    }

    handler = handlers.get(args.command)
    if handler:
        try:
            handler(args)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
