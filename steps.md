# minigit — Step-by-Step Walkthrough

This walks through the full workflow: hosting repos on `minigit_server.py`,
and using `minigit.py` to init, commit, clone, push, and pull against it.

All commands below assume `minigit.py` and `minigit_server.py` are in your
current directory (adjust the path otherwise).

---

## Part 1 — Start the server (your "GitHub")

1. **Start the server**

   ```bash
   python minigit_server.py --port 8000
   ```

   This creates a `storage/` folder (in the current directory, unless you
   pass `--storage <path>`) and starts listening on
   `http://localhost:8000`. Leave this running in its own terminal.

2. **Create a repo on the server**

   The server doesn't auto-create repos on first push — create one
   explicitly:

   ```bash
   curl -X PUT http://localhost:8000/repos/demo
   ```

   You should see `{"created": "demo"}`. You can list all repos with:

   ```bash
   curl http://localhost:8000/repos
   ```

   (If you'd rather skip this step and let `minigit.py` create the repo
   for you, see Part 7 below.)

---

## Part 2 — Clone, edit, commit, push

3. **Clone the (empty) repo**

   ```bash
   minigit clone http://localhost:8000/repos/demo work
   cd work
   ```

   This creates a `work/` folder with a `.minigit/` directory inside, and
   remembers the server URL as the repo's `origin` (in `.minigit/config`).

4. **Add a file and stage it**

    ```bash
    echo "hello world" > a.txt
    minigit add a.txt
    ```

    Or stage everything in the repo — including files in subdirectories —
    in one go:

    ```bash
    mkdir -p src/utils
    echo "print('hi')" > src/utils/helper.py
    minigit add .
    ```

    `add .` walks the whole repo tree recursively, so `src/utils/helper.py`
    gets staged as `src/utils/helper.py`, not just files sitting directly
    in `work/`.

    Two things get skipped automatically rather than staged:

    - any file **larger than 10 MB** (you'll see a warning naming the file
      and its size)
    - anything matched by a **`.miniignore`** file. Drop one anywhere in
      the project — it doesn't need to be at the root — with glob patterns
      like:

      ```
      *.log
      node_modules
      build/
      ```

      A bare name like `node_modules` ignores that whole directory and
      everything nested inside it, just like `.gitignore`.

5. **Commit the staged changes**

   ```bash
   minigit commit -m "first commit"
   ```

6. **Push the commit to the server**

   ```bash
   minigit push
   ```

   The server now has your commit, tree, and blob objects, and its
   `refs/heads/main` points at your new commit.

---

## Part 3 — A second clone, and syncing changes both ways

7. **Clone the repo again, somewhere else**

   ```bash
   cd ..
   minigit clone http://localhost:8000/repos/demo work2
   ```

   `work2/a.txt` already contains "hello world" — it was checked out from
   the commit you pushed in step 6.

8. **Make a change in `work2` and push it**

   ```bash
   cd work2
   echo "hi from work2" >> a.txt
   minigit add a.txt
   minigit commit -m "update from work2"
   minigit push
   cd ..
   ```

9. **Pull that change into the original `work` clone**

   ```bash
   cd work
   minigit pull
   cat a.txt
   cd ..
   ```

   `pull` fast-forwards `work` to match the server, fetching only the
   objects it doesn't already have.

---

## Part 4 — What happens when history diverges

10. **Create two independent commits from two clones without syncing**

    From `work`, make and push a commit. From `work2` (without pulling
    first), make a *different* commit and try to push:

    ```bash
    minigit push
    ```

    Because `work2`'s history isn't a fast-forward of the server's current
    HEAD, the server rejects it (HTTP 409):

    ```
    fatal: push rejected (409): rejected: not a fast-forward of the
    current HEAD (pull first, or retry with ?force=1)
    ```

    minigit is deliberately simple — there's no merging. The fix is
    normally to `pull` first. If you really want to overwrite the
    server's history anyway, you can force it:

    ```bash
    minigit push --force
    ```

---

## Part 5 — Local-path remotes (no server needed)

You don't need the HTTP server at all if you just want two repos on the
same filesystem to sync:

```bash
minigit init origin-repo
cd origin-repo
echo "hi" > f.txt
minigit add f.txt
minigit commit -m "initial"
cd ..

minigit clone origin-repo local-clone
```

For local-path remotes, use `pull` (from the clone) to fetch new commits
made directly in the origin folder. `push` only works against `http(s)`
origins served by `minigit_server.py`.

---

## Part 6 — Inspecting history

At any point inside a repo, check the commit log:

```bash
minigit log
```

---

## Part 7 — Connecting an existing folder to a brand-new remote

Everything above starts from `clone`, which only works once the remote
already has something to clone. If you instead already have a local
folder — `init`-ed, with commits — and want to hook it up to a fresh,
empty remote, use `remote --create` instead of `clone`:

```bash
cd my-existing-project
minigit init
minigit add .
minigit commit -m "first commit"

# creates the repo on the server (if it doesn't exist) AND
# saves it as this repo's origin
minigit remote http://localhost:8000/repos/my-existing-project --create

minigit push
```

From here on, `minigit push` and `minigit pull` in this folder no longer
need the URL — it's saved in `.minigit/config`, exactly as if you'd
cloned it in the first place. You can check what's currently configured
at any time with:

```bash
minigit remote
```

See `commands.md` for the full command reference.