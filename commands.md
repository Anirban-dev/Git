# minigit — Command Reference

Two programs:

- **`minigit.py`** — the client (init, add, commit, clone, remote, pull, push, log)
- **`minigit_server.py`** — the "GitHub"-style server that hosts repos over HTTP

---

## `minigit.py` commands

### `init [path]`

Create a new, empty minigit repository.

```bash
minigit init
minigit init my-project
```

| Argument | Required | Description |
|---|---|---|
| `path` | no (default `.`) | Where to create the `.minigit` directory |

---

### `add [<file/dir> ...]` or `add .`

Stage one or more files (or everything) for the next commit. Staging is
**recursive** — `add .` (or `add` with no arguments) walks the entire
repo tree, not just the current directory, so nested files under
subdirectories get staged too. Passing an explicit directory (`add src/`)
also walks it recursively.

```bash
# Stage specific files
minigit add a.txt
minigit add a.txt b.txt src/main.py

# Stage a directory (recursively)
minigit add src/

# Stage every file in the repo, at any depth
minigit add .

# Equivalent to `add .`
minigit add
```

Two things can cause a file to be skipped instead of staged:

- **Size limit** — files larger than **10 MB** are skipped with a warning
  (`warning: '<path>' (<bytes> bytes) exceeds the 10485760 byte limit,
  skipping`). This applies whether the file was named explicitly or
  picked up by a recursive `add .`.
- **`.miniignore`** — see below.

| Argument | Required | Description |
|---|---|---|
| `files` | no | File or directory paths to stage. Use `.` to stage everything in the repo, recursively. |

#### `.miniignore`

Add a `.miniignore` file anywhere in the project to exclude matching
files from `add`. It doesn't have to sit at the repo root — one can live
in any subdirectory, and patterns from **every** `.miniignore` found
anywhere in the tree apply globally to the whole repo.

Each line is a glob pattern (blank lines and lines starting with `#` are
ignored):

| Pattern | Matches |
|---|---|
| `*` | everything (ignores the whole repo) |
| `*.log` | anything ending in `.log`, anywhere in the tree |
| `build*` | anything starting with `build` |
| `node_modules` | that directory, and everything nested inside it (no wildcard needed for a plain directory/file name) |

A pattern is checked against the file's full repo-relative path, its
basename, and every individual path segment — so a bare directory name
like `node_modules` or `logs` ignores everything underneath it, the same
way `.gitignore` would.

```bash
# Example .miniignore
*.log
node_modules
build/
.DS_Store
```

Running `add` prints a one-line summary of how many files were skipped
for being ignored (`Ignored 3 file(s) per .miniignore`).

---

### `commit -m "<message>" [--author <name>]`

Record everything currently staged as a new commit.

```bash
minigit commit -m "add login form"
minigit commit -m "fix typo" --author "Jane Doe"
```

| Flag | Required | Description |
|---|---|---|
| `-m`, `--message` | yes | Commit message |
| `--author` | no | Overrides the author (defaults to `$USER`) |

---

### `clone <source> <destination>`

Clone a repository into a new directory. `source` can be:

- a **local path** to another minigit repo, or
- an **`http(s)://` URL** pointing at a repo on `minigit_server.py`
  (e.g. `http://localhost:8000/repos/demo`)

```bash
minigit clone ../other-repo my-clone
minigit clone http://localhost:8000/repos/demo my-clone
```

| Argument | Required | Description |
|---|---|---|
| `source` | yes | Local path or URL to clone from |
| `destination` | yes | Path to create the clone in (must not exist, or be empty) |

The source is remembered as `origin` for later `pull` / `push` calls.

> `clone` requires the remote to already exist. If you instead have a
> local folder you've already `init`-ed and want to connect it to a
> brand-new, empty remote, use `remote --create` (below) rather than
> `clone`.

---

### `remote [<url>] [--create]`

Show or set the repo's `origin` — the same field `clone` writes to
`.minigit/config` automatically. This is how you connect an
already-initialized local folder to a remote without going through
`clone` (useful when the remote repo doesn't exist yet, or you just want
to skip retyping the URL on every `pull`/`push`).

```bash
# Show the current origin
minigit remote

# Set the origin (repo must already exist on the server)
minigit remote http://localhost:8000/repos/demo

# Set the origin AND create the repo on the server if it isn't there yet
minigit remote http://localhost:8000/repos/demo --create
```

| Argument / Flag | Required | Description |
|---|---|---|
| `url` | no | Origin to set (path or URL). Omit to just print the current origin. |
| `--create` | no | Also sends `PUT /repos/<name>` to create the repo on the server first. `http(s)` origins only. A repo that already exists (`409`) is treated as fine, not an error. |

Typical use — connecting a fresh local folder to a fresh remote:

```bash
minigit init
minigit add .
minigit commit -m "first commit"
minigit remote http://localhost:8000/repos/demo --create
minigit push
```

After `remote` sets the origin, `pull` and `push` no longer need the URL
passed in every time.

---

### `pull [remote]`

Fast-forward the current repo from its origin (or an explicit remote).
Works with both local-path and `http(s)` origins. Fails if history has
diverged (minigit only supports fast-forward pulls — no merging).

```bash
minigit pull
minigit pull http://localhost:8000/repos/demo
minigit pull ../other-repo
```

| Argument | Required | Description |
|---|---|---|
| `remote` | no | Overrides the configured origin (path or URL) |

---

### `push [remote] [--force]`

Push local commits to an `http(s)` origin hosted by `minigit_server.py`.
The server rejects the push (HTTP 409) unless it's a fast-forward of its
current HEAD.

```bash
minigit push
minigit push http://localhost:8000/repos/demo
minigit push --force
```

| Argument / Flag | Required | Description |
|---|---|---|
| `remote` | no | Overrides the configured origin (must be a URL) |
| `--force` | no | Skips the server's fast-forward check |

> Local-path remotes don't support `push` — pull from the other side instead.
> The target repo must already exist on the server — either create it with
> `curl -X PUT` (see below) or `minigit remote <url> --create`.

---

### `log`

Show commit history from HEAD backwards (bonus command, not in real Git's
minimal set but handy for sanity-checking everything above).

```bash
minigit log
```

---

## `minigit_server.py` — server startup

```bash
python minigit_server.py [--host 0.0.0.0] [--port 8000] [--storage ./storage]
```

| Flag | Default | Description |
|---|---|---|
| `--host` | `0.0.0.0` | Interface to bind |
| `--port` | `8000` | Port to listen on |
| `--storage` | `storage` | Directory where hosted repos are stored |

---

## `minigit_server.py` — HTTP API

All of these are also what `minigit.py clone/pull/push/remote --create`
call under the hood; use `curl` directly for repo administration
(creating/listing repos).

| Method | Path | Description |
|---|---|---|
| `GET` | `/repos` | List all hosted repo names → `{"repos": [...]}` |
| `PUT` | `/repos/<name>` | Create a new, empty repo (`201`) or `409` if it exists |
| `GET` | `/repos/<name>` | Download a zip archive of the repo (used by `clone`/`pull`) |
| `GET` | `/repos/<name>/archive` | Same as above, explicit form |
| `GET` | `/repos/<name>/head` | Current HEAD commit → `{"head": "<sha1>"|null}` |
| `POST` | `/repos/<name>/push` | Body: zip archive of a `.minigit` dir. `409` if not a fast-forward; add `?force=1` to override |

### Examples

```bash
# create a repo
curl -X PUT http://localhost:8000/repos/demo

# list repos
curl http://localhost:8000/repos

# check current HEAD
curl http://localhost:8000/repos/demo/head

# download the raw archive (rarely needed directly — minigit.py does this for you)
curl http://localhost:8000/repos/demo -o demo.zip
```