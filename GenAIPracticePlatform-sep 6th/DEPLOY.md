# Deploy — foolproof steps

## What is actually wrong (checked 2026-09-07)

The repo `nithyasatheesh/GenAI_AgenticAI_Coding-Platform` has **two copies** of
this app in subfolders:

| Folder | its `requirements.txt` | builds on Streamlit Cloud? |
|---|---|---|
| `GenAIPracticePlatform/` | OLD — `langgraph`, `chromadb`, `fastembed`, `mcp` | **NO** — these compile Rust/C++ and fail the build |
| `GenAIPracticePlatform-6th sep/` | the good lean one (this bundle) | yes |

Streamlit Cloud is still pointed at `GenAIPracticePlatform/streamlit_app.py`, so
every build reinstalls `chromadb` / `fastembed` / `langgraph` and dies. The build
log's "Error installing requirements" is that — not your code.

### Fastest fix — no git, one setting

Streamlit Cloud → **Manage app → Settings → Main file path** →

```
GenAIPracticePlatform-6th sep/streamlit_app.py
```

→ **Save** → **Reboot app**. It now reads the lean `requirements.txt` next to it.

If the space in the folder name is rejected, rename the folder on GitHub (edit
`…-6th sep/streamlit_app.py`, retype its path to `app/streamlit_app.py`, commit;
repeat for `sandbox.py`, `grader.py`, `mcp_server.py`, `requirements.txt`, and the
`content/…` files) and set Main file path to `app/streamlit_app.py`.

### Cleaner fix — put THIS bundle at the repo root

Unzip this bundle and run (from the folder that has `streamlit_app.py` in it):

```bash
./push-to-github.sh https://github.com/nithyasatheesh/GenAI_AgenticAI_Coding-Platform.git
```

(PowerShell: `powershell -ExecutionPolicy Bypass -File .\push-to-github.ps1 <url>`)

That force-replaces the repo with these files at the **root**, so Main file path
is just `streamlit_app.py`. NOTE: `--force` also removes the `GenAILabKit/`
folder — copy it out first if you want to keep it.

Then delete the old `GenAIPracticePlatform/` folder so this cannot recur.

---

The `requirements.txt` in this bundle is 9 unpinned pure-wheel packages —
zero need a compiler, so the Streamlit Cloud (`uv`) build cannot fail on them.

---

## Option A — overwrite your existing repo (fastest)

From **this unzipped folder** (the one with `streamlit_app.py` in it):

```bash
git init
git add -A
git commit -m "practice platform — pure-wheel requirements"
git branch -M main
git remote add origin https://github.com/<you>/<your-repo>.git
git push -u --force origin main
```

`--force` replaces whatever is in the repo now. Then in Streamlit Cloud:
**Manage app → Reboot app**.

## Option B — brand-new repo (zero doubt)

1. github.com → **New repository** → *don't* add a README/`.gitignore`.
2. Same commands as Option A with the new repo URL (drop `--force`).
3. share.streamlit.io → **Create app** → that repo, branch `main`,
   **Main file path: `streamlit_app.py`**.
4. **Advanced settings → Python 3.11**.
5. Deploy.

---

## Check the layout is right

At the **repo root** (not in a subfolder) you must see:

```
streamlit_app.py
sandbox.py
mcp_server.py
requirements.txt          ← the 10-line pure-wheel file
requirements-full.txt     ← optional, do NOT point Cloud at this one
requirements-min.txt      ← escalation fallback (7 lines) if the build still fails
content/
```

If `streamlit_app.py` ends up inside `practice-platform/streamlit_app.py` in the
repo, Streamlit can't find it — move everything up one level.

---

## Escalation ladder — swap in this order, push + Reboot after each

| # | requirements.txt = | Runs | If it still fails |
|---|---|---|---|
| 1 | `requirements.txt` (9 lines, no langgraph) | Labs 1, 2 | → 2 |
| 2 | contents of `requirements-min.txt` (7 lines, no openai/anthropic) | Lab 1 + graded UI | → 3 |
| 3 | contents of `requirements-diagnostic.txt` (`streamlit` + `pyyaml`) | app boots only | → **not the packages** |

If **step 3** fails — a repo whose `requirements.txt` is literally two lines,
`streamlit` and `pyyaml` — then the problem is not Python packages. Check on
**github.com** in a browser:

- `requirements.txt` in the repo shows those 2 lines (not an old file)?
- `streamlit_app.py` is at the **repo root**, not inside `practice-platform/`?
- The repo's "latest commit" timestamp is your last push?
- Streamlit Cloud app settings point at that repo + `main` + `streamlit_app.py`?

## I need the actual error to go further

Manage app → the **black terminal panel** (not the 😦 page) → scroll to the first
red line and copy the **~10 lines above it** as text. That names the package.

---

## After it deploys

- It starts in **Mock mode** (no key) — Lab 1 (RAG) runs fully.
- For real LLM + Labs 2–4: **Manage app → Settings → Secrets** →
  `OPENAI_API_KEY = "sk-..."` (a **valid** key — the one currently in your env
  returns HTTP 401). The sidebar tests the key on load and shows a red box if
  it's rejected.
