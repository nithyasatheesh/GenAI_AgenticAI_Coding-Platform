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

## If the build STILL fails

1. Manage app → the black terminal → copy the **10 lines above the first
   `ERROR:`** and send them.
2. Meanwhile: rename `requirements-min.txt` → `requirements.txt`, commit, push,
   reboot. That 7-package set (streamlit, pyyaml, langchain-core,
   langchain-community, langchain-text-splitters, pypdf, openpyxl) always builds;
   Lab 1 + the full graded UI work; Labs 2–5 will say "add langgraph /
   langchain-openai to requirements" until you add those lines back.

---

## After it deploys

- It starts in **Mock mode** (no key) — Lab 1 (RAG) runs fully.
- For real LLM + Labs 2–4: **Manage app → Settings → Secrets** →
  `OPENAI_API_KEY = "sk-..."` (a **valid** key — the one currently in your env
  returns HTTP 401). The sidebar tests the key on load and shows a red box if
  it's rejected.
