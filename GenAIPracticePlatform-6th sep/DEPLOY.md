# Deploy — Streamlit Community Cloud

## The dependency fix (2026-09-07)

**Root cause of "installer returned a non-zero exit code / Error during
processing dependencies":** the build was running on **Python 3.13**, and three
native wheels in the stack — `chroma-hnswlib` (only when an old `chromadb` is
pulled), `ormsgpack` (via `langgraph`), `py-rust-stemmers` (via `fastembed`) —
had **no cp313 wheel**, so `uv` tried to compile them from source, and the Cloud
build image has no Rust/C++ toolchain → non-zero exit. The `rich` /
`markdown-it-py` / `pygments` churn in the log is normal pip resolution, not the
failure.

**Fix, two parts, both in this bundle:**

1. **`.python-version` = `3.12`** and **`runtime.txt` = `python-3.12`** — pin the
   build to 3.12, where every package in `requirements.txt` has a prebuilt
   manylinux wheel (verified: full clean resolution, 143 packages, 0 that need a
   compiler). Also set **Advanced settings → Python 3.12** in the Cloud app (the
   dropdown wins if it disagrees with the files).
2. **`requirements.txt` rewritten** — exactly one line per capability the app +
   labs actually `import` (checked against every `.py` and every
   `content/*/practice.yaml`), no umbrella `langchain`, no transitive pins, no
   unused libs. See the file's own header for the per-line reason.

If the build still fails *after* pinning 3.12, it is **build memory**, not
wheels. Delete the `fastembed` line from `requirements.txt` (Mock mode then uses
`DeterministicFakeEmbedding` automatically — still keyless, still works); that
drops the heaviest branch (`py-rust-stemmers`, `onnxruntime`, `huggingface_hub`).
Next fallback: rename `requirements-min.txt` → `requirements.txt` (Labs 1–2 +
graded UI; no chromadb / langgraph / mcp).

---

## Which folder does Cloud build?

The repo `nithyasatheesh/GenAI_AgenticAI_Coding-Platform` has the app in a
subfolder (`GenAIPracticePlatform/` and a newer `GenAIPracticePlatform-6th sep/`).
Streamlit Cloud builds **the folder that contains the file in "Main file path"**
and installs **the `requirements.txt` next to that file**. So the fix must land
in whichever folder Main file path points at — check **Manage app → Settings →
Main file path** and update the `requirements.txt` / `.python-version` /
`runtime.txt` in *that* folder (or point Main file path at the folder that has
the fixed files).

Cleanest: put this bundle at the **repo root** so there is only one copy —

```bash
git clone https://github.com/nithyasatheesh/GenAI_AgenticAI_Coding-Platform.git
cd GenAI_AgenticAI_Coding-Platform
# copy the contents of this bundle into the repo root, replacing old copies
git rm -r --quiet "GenAIPracticePlatform" "GenAIPracticePlatform-6th sep"   # optional cleanup
cp -r /path/to/this/bundle/* /path/to/this/bundle/.python-version .
git add -A
git commit -m "deploy: clean requirements, pin Python 3.12"
git push
```

Then set **Main file path = `streamlit_app.py`**, **Python = 3.12**, **Reboot app**.

---

## Verify the layout

At the folder Cloud builds you must see:

```
streamlit_app.py
grader.py
sandbox.py
mcp_server.py
requirements.txt         ← the capability-complete file
.python-version          ← 3.12
runtime.txt              ← python-3.12
content/
```

---

## After it deploys

- Starts in **Mock mode** (no key) — Lab 1 (RAG) runs fully; Labs 3–5 (agents /
  MCP) need a real key.
- Real LLM: **Manage app → Settings → Secrets** →
  `OPENAI_API_KEY = "sk-..."` or `ANTHROPIC_API_KEY = "sk-ant-..."`. The sidebar
  makes one tiny test call on load and shows a red box if the key is rejected.
- Keys are read only from the environment / Streamlit secrets — never hard-coded,
  never sent to the browser.
