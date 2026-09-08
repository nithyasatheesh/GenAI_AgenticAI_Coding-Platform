# GenAI Lab — Practice Platform

Hands-on practice for **real** GenAI / Agentic-AI engineering. Five labs, five
tasks each. Every task: **starter code → your editor → Run → real output →
execution steps → real errors → hints → solution → score**.

**Scoring** — each lab is out of **100**. The RAG lab (`01-rag`) is weighted
**T1 5 · T2 20 · T3 25 · T4 25 · T5 25**; other labs use their YAML `weight:`.
The **★ Score** page exports the result as an **Excel `.xlsx`** (summary + a
per-task table + total), with CSV / JSON fallbacks.

**Grading engine** (`grader.py`) — the RAG lab is graded criterion-by-criterion:
each task has an explicit rubric (e.g. `chunk_size_1000`, `documents_split`,
`answer_generated_by_llm`) and each criterion is verified independently by
**parsing the learner's submitted code (AST)** *and* **executing Task 1…N and
inspecting the real objects it produced** (was a `Document` list actually built?
did `similarity_search` return 3 hits? is the printed answer produced by the LLM
from retrieved context, or hardcoded?). Marks are awarded per criterion, so
partial work earns partial credit and *running successfully never by itself earns
full marks*. Tick **🔧 Developer mode** in the sidebar (or add `?dev=1`) to see
every criterion's pass/fail, points, reason, and the exact source the grader ran.
Labs without a rubric in `grader.py` fall back to the legacy regex checks.
Run `python grader_tests.py` for the 8-case self-test.

Self-contained and Streamlit-Community-Cloud ready (`streamlit_app.py` +
`requirements.txt` at the repo root, no arguments).

```
practice-platform/
├── streamlit_app.py     # the app
├── grader.py            # criterion-based grading engine (RAG lab)
├── grader_tests.py      # 8-case self-test for grader.py  →  python grader_tests.py
├── sandbox.py           # runtime helpers injected into every Run
├── mcp_server.py        # a real FastMCP server the MCP lab connects to
├── requirements.txt      # LEAN — builds on Streamlit Community Cloud (Labs 1–2 + full graded UI)
├── requirements-full.txt # + ChromaDB, LangGraph, MCP, FastEmbed — local / paid tier / container
├── requirements-min.txt  # absolute floor if even the lean file won't build
└── content/
    ├── _data/                   sample PDFs
    ├── 01-rag/practice.yaml     RAG: PyPDFLoader → splitter → embeddings → vector store → grounded answer
    ├── 02-tool-calling/…        bind_tools → tool_calls → execute → ToolMessage loop
    ├── 03-agent/…               LangGraph create_react_agent (ReAct loop, streaming, custom tool)
    ├── 04-multi-agent/…         supervisor + researcher + analyst on a StateGraph
    └── 05-mcp/…                 MultiServerMCPClient ⇄ mcp_server.py over stdio; agent over MCP tools
```

---

## What is real vs. a stand-in

**Real in every mode — never simulated:**

| Piece | How |
|---|---|
| Python execution | `exec()` in *this app's* interpreter. Real stdout/stderr, real tracebacks. |
| LangChain / LangGraph | genuine objects — loaders, splitters, prompts, chains, `StateGraph`, `create_react_agent` |
| Vector store | **real ChromaDB** (`chromadb.EphemeralClient`) — in `requirements.txt`. Auto-falls back to `langchain-core` **`InMemoryVectorStore`** (same interface, real cosine retrieval) if chromadb ever fails to import. `make_vectorstore()` picks whichever is importable. |
| Embeddings | **OpenAI mode → real `OpenAIEmbeddings`**. Keyless → real local **FastEmbed** ONNX model (in `requirements.txt`); if that line is removed, a deterministic fallback keeps Mock mode working (weaker retrieval — use OpenAI mode for real keyless embeddings). |
| MCP | in `requirements.txt`. `mcp_server.py` (FastMCP) is launched as a **real subprocess**; `langchain-mcp-adapters` speaks MCP over stdio. |
| Tools | real LangChain `@tool` objects (`calculator`, `word_count`, `kb_lookup`) |

**Mode-dependent — the LLM:**

| Mode | Chat model | Needs |
|---|---|---|
| **OpenAI** (primary) | `ChatOpenAI` (default `gpt-4o-mini`, override `OPENAI_MODEL`) | `OPENAI_API_KEY` |
| **Claude** (primary) | `ChatAnthropic` (default `claude-sonnet-4-5`, override `ANTHROPIC_MODEL`) | `ANTHROPIC_API_KEY` |
| **Mock** (demo fallback) | a local `BaseChatModel` that answers from retrieved context — **cannot do tool calling** | nothing |

The app **defaults to a real mode** when a key is present, else Mock. Labs
2–4 (`mode_required: real`) and MCP tasks 4–5 (`needs_real`) are blocked in Mock
with a clear message — they are **not** faked.

---

## Where learner code runs, and the API key

Run does `exec(compile(source), namespace)` in the **same Python interpreter that
runs Streamlit** — no subprocess (except the MCP lab, which deliberately spawns
`mcp_server.py`).

- The API key is read **only** from an environment variable / server-side secret
  (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). It is never hard-coded and never sent
  to the browser.
- Local: `export OPENAI_API_KEY=sk-…`
- Cloud: **Manage app → Settings → Secrets** → `OPENAI_API_KEY = "sk-…"`
- With **no key**, Mock mode still runs Lab 1 (RAG) and Lab 5 tasks 1–3 fully.

---

## Run locally

```bash
cd practice-platform
python -m venv .venv && .venv\Scripts\activate       # (source .venv/bin/activate on mac/linux)
pip install -r requirements.txt
streamlit run streamlit_app.py
```

To use real LLMs, set `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`) first. The first
Run of Lab 1 in keyless mode downloads the ~90 MB FastEmbed model once.

## Deploy to Streamlit Community Cloud

1. Put the contents of this folder at the repo root (or point **Main file path**
   at this folder), push to GitHub.
2. share.streamlit.io → **Create app** → your repo, `main`, **main file
   `streamlit_app.py`**, **Advanced settings → Python 3.12** (must match
   `.python-version`).
3. The build installs `requirements.txt` — a **full clean resolve of 143
   packages, exit 0, every native wheel prebuilt for cp312** (no compiler). See
   `DEPLOY.md` for the exact root-cause analysis and fallbacks.
4. **Settings → Secrets** → add `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`) to turn
   on real LLM mode + real OpenAI embeddings + Labs 3–5.

| Deploy log says | Fix |
|---|---|
| `installer returned a non-zero exit code` while building a rust/C++ crate (`ormsgpack`, `py-rust-stemmers`, `chroma-hnswlib`) | the build is on Python 3.13 — set **Python 3.12** in Advanced settings (and confirm `.python-version` / `runtime.txt` are in the built folder), Reboot. |
| build fails and the log shows an OOM / killed process | delete the `fastembed` line from `requirements.txt` (Mock mode falls back to `DeterministicFakeEmbedding`); if still failing, rename `requirements-min.txt` → `requirements.txt`. |
| `ModuleNotFoundError: chromadb` / `mcp` at runtime | the built folder's `requirements.txt` is an old copy — replace it with this one. |
| Run: `OpenAIAuthenticationError 401` | the real API rejected the key — set a valid `OPENAI_API_KEY` in Secrets |
| MCP lab: `FileNotFoundError` on the server | `mcp_server.py` must be at the repo root next to `streamlit_app.py` |

---

## The labs

| # | Lab | Tasks | Mode |
|---|-----|-------|------|
| 1 | **RAG with ChromaDB** | load → chunk → embed+index (Chroma) → grounded answer → interactive loop | any (Mock ok) |
| 2 | **Tool Calling** | inspect tools → `bind_tools` + one call → execute + `ToolMessage` → tool loop → tool-calling RAG | real |
| 3 | **Agent (LangGraph ReAct)** | build+run `create_react_agent` → persona → stream steps → inspect graph → custom tool | real |
| 4 | **Multi-Agent (LangGraph)** | two ReAct workers → supervisor `with_structured_output` → wire `StateGraph` → run crew → add reviewer | real |
| 5 | **MCP** | connect+discover → call an MCP tool → read a resource → MCP tools + model → ReAct agent over MCP | 1–3 any, 4–5 real |

Add a lab: drop `content/<id>/practice.yaml` (keys: `lab_id`, `title`,
`requires`, optional `mode_required`, `overview`, `tasks[]` with
`id/title/prompt/hints/starter/solution/checks`, optional per-task `needs_real`).
