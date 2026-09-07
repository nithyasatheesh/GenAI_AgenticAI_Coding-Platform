# Deploy — Streamlit Community Cloud

## The dependency fix (2026-09-07)

**What the build log actually shows:** pip runs to completion —
`Successfully installed …` — and *then* the Community Cloud wrapper prints
`installer returned a non-zero exit code` / `Error during processing
dependencies`. That is not a version conflict and not a missing wheel (there is
no `ERROR: No matching distribution` / `ResolutionImpossible`). It is the
**free-tier build exceeding its memory/disk limit** while unpacking the heavy
tree: `chromadb` + `onnxruntime` + `fastembed` + `langgraph` + `pyarrow` +
`numpy` together. The `rich` / `markdown-it-py` / `pygments` uninstall/reinstall
churn is normal pip resolution — not the failure.

**Fix: `requirements.txt` in this bundle is now the LEAN set** — no `chromadb`,
`langgraph`, `fastembed`, `mcp`, `onnxruntime`. It builds on Community Cloud in
~1 minute (pure-Python). The app degrades gracefully:

| Lab | On the lean `requirements.txt` |
|---|---|
| 1 · RAG | **full** — `InMemoryVectorStore` instead of ChromaDB; OpenAI embeddings, or the built-in `DeterministicFakeEmbedding` in Mock mode |
| 2 · Tool calling | **full** |
| 3–5 · LangGraph / multi-agent / MCP | blocked on Run with a clear message — need `requirements-full.txt` |
| Grading engine + Excel export + Mock/OpenAI/Claude modes | unaffected |

`requirements-full.txt` (`-r requirements.txt` + chromadb, langchain-chroma,
langgraph, mcp, langchain-mcp-adapters, fastembed) is for a **real machine /
paid tier / container** — with `.python-version` = 3.12 so every native wheel is
prebuilt. `requirements-min.txt` is an even smaller floor if the lean file
somehow still fails.

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
