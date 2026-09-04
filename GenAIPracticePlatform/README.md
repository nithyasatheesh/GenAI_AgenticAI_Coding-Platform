# GenAI Lab — Practice Platform

Interactive practice UI for guided GenAI / Agentic-AI labs. Per task: the question,
progressive hints, a code editor, a **Reveal solution** toggle, an auto-scored
**Check**, and a **real Run** that executes the learner's code.

Self-contained and **Streamlit-Community-Cloud ready** — `streamlit_app.py` and
`requirements.txt` at the repo root, no arguments.

```
practice-platform/
├── streamlit_app.py          # the app (entry point)
├── sandbox.py                # runtime helpers injected into every Run (mock / OpenAI / Claude model + embeddings)
├── requirements.txt          # minimal: streamlit, pyyaml, langchain-core/-community/-text-splitters, langgraph, pypdf  <-- MUST be at repo root
├── content/
│   ├── pdf-rag-knowledge-base/
│   │   ├── practice.yaml      # tasks: prompt / hints / starter / solution / checks / requires
│   │   └── data/              # bundled sample PDFs (real files, loaded for real)
│   └── langchain-basics/
│       └── practice.yaml      # LCEL chain + LangGraph state machine
└── .gitignore
```

---

## Where learner code runs (read this)

**The Run button executes learner code with `exec()` inside the *same Python
interpreter that runs the Streamlit server*.** There is no second sandbox, no
subprocess, no container-in-container.

| Deployment | Interpreter that runs Streamlit **and** learner code | Where packages come from |
|---|---|---|
| **Local** | your virtualenv's `python` | `pip install -r requirements.txt` into that venv |
| **Streamlit Community Cloud** | the app container's Python (3.12) | Cloud runs `pip install -r requirements.txt` at build time |

Consequences:

- Every package in `requirements.txt` is importable from learner code — that's why
  `import langchain_community…` works.
- **`requirements.txt` is deliberately minimal** — only what the app, `sandbox.py`,
  and the exercise code actually import: `streamlit`, `pyyaml`, `langchain-core`,
  `langchain-community`, `langchain-text-splitters`, `langgraph`, `pypdf`.
  It does **not** include `chromadb`/`langchain-chroma` (they don't build reliably
  on Streamlit Cloud — the sandbox uses `langchain_core.vectorstores.InMemoryVectorStore`,
  same API), the `langchain` meta-package (unused), or `langchain-openai` /
  `langchain-anthropic` (OpenAI / Claude modes only — opt-in, see below).
- Before each Run, the app checks the lab's `requires:` list with
  `importlib.util.find_spec`. **If a package is missing, Run stops and says which
  one — it does not mock, catch, or fake the result.**
- State accumulates like notebook cells: Run concatenates Task 1 → N and executes
  them together, so Task 3 can use `chunks` from Task 2.
- A short **preamble** is prepended to every Run (it is not shown in the editor):

  ```python
  import sandbox
  from sandbox import (get_chat_model, get_embeddings, load_sample_docs,
                       make_vectorstore, SAMPLE_PDF)
  MODE = "mock"   # "mock" | "openai" | "claude", from the sidebar
  ```

---

## LLM modes — Mock / OpenAI / Claude

Chosen in the sidebar. **The LangChain pipeline is identical in all three** —
loaders, splitters, the vector store, retrievers, prompts, chains and graphs are
all real. Only the model (and, for OpenAI, the embeddings) swaps.

| | 🧪 **Mock** | 🔷 **OpenAI** | 🟣 **Claude** |
|---|---|---|---|
| API key | none | `OPENAI_API_KEY` | `ANTHROPIC_API_KEY` |
| Package (opt-in) | — | `langchain-openai` | `langchain-anthropic` |
| `get_chat_model(MODE)` | local `BaseChatModel` that answers from the retrieved `Context:` (or refuses) | `ChatOpenAI` (default `gpt-4o-mini`, override `OPENAI_MODEL`) | `ChatAnthropic` (default `claude-sonnet-4-5`, override `ANTHROPIC_MODEL`) |
| `get_embeddings(MODE)` | `DeterministicFakeEmbedding` | `OpenAIEmbeddings` (`text-embedding-3-small`) | `DeterministicFakeEmbedding` — *Anthropic has no embeddings API, so retrieval is local; only answer generation is real Claude* |
| Cost | free | your OpenAI account | your Anthropic account |

**Both real modes are opt-in** so the default deploy stays minimal:

1. In `requirements.txt`, uncomment `langchain-openai` and/or `langchain-anthropic`; redeploy.
2. Add the key:
   - **Local:** `export OPENAI_API_KEY=sk-…` or `export ANTHROPIC_API_KEY=sk-ant-…`
   - **Cloud:** *Manage app → Settings → Secrets* → `OPENAI_API_KEY = "sk-…"` / `ANTHROPIC_API_KEY = "sk-ant-…"` (and `ANTHROPIC_MODEL = "…"` if your account's Claude model id differs from the default).

Until a mode's package is installed, its Run stops with a clear "uncomment `langchain-…` and redeploy" message. **Mock mode needs none of this.**

---

## Run locally

```bash
cd practice-platform
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt    # installs into THIS venv — the one Streamlit will use
streamlit run streamlit_app.py
```

Mock mode works immediately. For OpenAI/Claude mode, uncomment the package in `requirements.txt` and set the matching key (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`).

---

## Deploy to Streamlit Community Cloud

1. Put **the contents of this folder at the repo root** (so `streamlit_app.py` and
   `requirements.txt` are top-level):

   ```bash
   cd practice-platform
   git init && git add . && git commit -m "GenAI Lab practice platform"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```

2. <https://share.streamlit.io> → **Create app** → your repo, branch `main`,
   **Main file path = `streamlit_app.py`**.
3. *Advanced settings* → Python **3.12** (3.11/3.13 also fine) → **Deploy**.
   First build installs ~30 s of pure-Python wheels — no native compilation.
4. (Optional) for OpenAI/Claude mode: uncomment `langchain-openai` / `langchain-anthropic` in `requirements.txt`, then add `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` in *Settings → Secrets*.

Open a specific lab with `?lab=<folder-name>` in the URL.

### Deploy errors → fixes

| Log message | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'yaml'` / `'langchain_community'` … | `requirements.txt` isn't at the repo root, or the build didn't finish — it must sit next to `streamlit_app.py` at the top level; redeploy / "Reboot app". |
| `No content found` / `FileNotFoundError: .../content/...` | `content/` wasn't committed, or `streamlit_app.py` isn't at the repo root. |
| Run says **"Cannot Run — packages missing"** | The app's env is missing that package. It's in `requirements.txt`; *Manage app → Reboot app* to reinstall. |
| Run in OpenAI/Claude mode: `AuthenticationError`, `NotFoundError` (wrong Claude model id), or "needs `…_API_KEY`" | Add the key in *Settings → Secrets*; for Claude also set `ANTHROPIC_MODEL` to a model your account has. Or use Mock mode. |
| Run says **"uncomment `langchain-openai` / `langchain-anthropic`"** | That real mode's package isn't installed — uncomment it in `requirements.txt`, commit, *Reboot app*. |
| `git push` → `Authentication failed` | Use a GitHub Personal Access Token / `gh auth login`, not your password. |

---

## Add another lab

Create `content/<id>/practice.yaml`:

```yaml
lab_id: <id>
title: <Title>
requires: [langchain_core, langgraph, ...]   # import names, checked before Run
tasks:
  - id: 1
    title: ...
    prompt: |
      markdown
    hints: ["...", "...", "..."]
    starter: |
      # TODO
    solution: |
      # full runnable reference (may use MODE / get_chat_model / get_embeddings / SAMPLE_PDF)
    checks:
      - {id: c1, points: 3, pattern: "regex over the learner's code", desc: "..."}
```

It appears in the sidebar automatically. **Every task's `solution` should Run
cleanly in Mock mode** and score full marks on Check.

---

## What this is / isn't

- **Is:** a hosted, runnable practice-and-self-check environment for GenAI /
  Agentic-AI lab content, offline by default.
- **Isn't:** the graded VM lab. The full guided notebooks, VM provisioning,
  `grade_submission.py` (0–100 grader) and `validate_solution.py` (vendor QA)
  live in `../genai-lab-kit/`.
