import os
import fnmatch

DEFAULT_IGNORES = [
    ".minigit",
    ".git",
    "__pycache__",
    "*.pyc",
    "storage",
    "node_modules",
    ".env",
    "dist"
]

class IgnoreMatcher:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.patterns = list(DEFAULT_IGNORES)
        self._load_ignore_file()

    def _load_ignore_file(self):
        ignore_file = os.path.join(self.repo_path, ".miniignore")
        if os.path.isfile(ignore_file):
            with open(ignore_file, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self.patterns.append(line)

    def is_ignored(self, rel_path: str) -> bool:
        """
        Checks if relative path should be ignored.
        """
        norm_path = rel_path.replace("\\", "/")
        parts = norm_path.split("/")

        for pattern in self.patterns:
            # Match top-level or subpath pattern
            if fnmatch.fnmatch(norm_path, pattern):
                return True
            for part in parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
        return False
