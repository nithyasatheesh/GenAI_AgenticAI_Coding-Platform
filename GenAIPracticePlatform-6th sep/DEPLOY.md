# Deploy — foolproof steps

Your last failed build was installing packages that don't build on Streamlit
Cloud (`chromadb` / `fastembed` / `onnxruntime` / rust crates). That means the
repo GitHub is serving to Streamlit **has an old `requirements.txt`**. Push the
files from this folder and it will build.

`uv pip compile` (the exact resolver Streamlit Cloud uses) resolves the
`requirements.txt` in this folder to **91 packages on Python 3.11 / 3.12 / 3.13**,
with zero packages that need a compiler.

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
