# GenAI Lab — Practice Platform

Hands-on practice for **real** GenAI / Agentic-AI engineering. Five labs, five
tasks each. Every task: **starter code → your editor → Run → real output →
execution steps → real errors → hints → solution → score**.

Self-contained and Streamlit-Community-Cloud ready (`streamlit_app.py` +
`requirements.txt` at the repo root, no arguments).

```
practice-platform/
├── streamlit_app.py     # the app
├── sandbox.py           # runtime helpers injected into every Run
├── mcp_server.py        # a real FastMCP server the MCP lab connects to
├── requirements.txt     # the full real stack (verified: fresh-venv install, exit 0)
└── content/
    ├── _data/                   sample PDFs
    ├── 01-rag/practice.yaml     RAG: PyPDFLoader → splitter → FastEmbed → ChromaDB → grounded answer
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
| Vector store | **real ChromaDB** (`chromadb.EphemeralClient`); auto-fallback to `InMemoryVectorStore` only if chromadb can't import |
| Embeddings | **real** — `OpenAIEmbeddings` (OpenAI mode) or a local **FastEmbed** ONNX model (`BAAI/bge-small-en-v1.5`, no key). `DeterministicFakeEmbedding` is a last resort and prints a warning. |
| MCP | `mcp_server.py` (FastMCP) is launched as a **real subprocess**; `langchain-mcp-adapters` speaks MCP JSON-RPC over stdio |
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

First Run of Lab 1 downloads the ~90 MB FastEmbed model once. To use real LLMs,
set `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`) first.

## Deploy to Streamlit Community Cloud

1. Put the contents of this folder at the repo root, push to GitHub.
2. share.streamlit.io → **Create app** → your repo, `main`, **main file
   `streamlit_app.py`**, Python **3.12**.
3. First build installs the full stack (~2–4 min — chromadb, onnxruntime,
   fastembed). Verified to resolve cleanly (144 packages, exit 0).
4. Add `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` in **Settings → Secrets** to enable
   the real LLM modes and Labs 2–4.

| Deploy log says | Fix |
|---|---|
| `ModuleNotFoundError` for a lab package | build didn't finish or a dep was removed — Reboot app; keep `requirements.txt` intact |
| Run: `OpenAIAuthenticationError 401` | that's the real API rejecting the key — set a valid `OPENAI_API_KEY` in Secrets |
| MCP lab: `FileNotFoundError` on the server | `mcp_server.py` must be at the repo root next to `streamlit_app.py` |
| Lab 1: `[sandbox] ChromaDB unavailable …` in the output | chromadb didn't install; the lab still runs on the in-memory fallback |

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
