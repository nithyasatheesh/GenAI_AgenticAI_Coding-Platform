# GenAI Lab — Practice Platform

Interactive practice UI for guided GenAI / Agentic-AI labs. Per task: the question,
progressive hints, a code editor, a **Reveal solution** toggle, an auto-scored
**Check**, and a **real Run** that executes the learner's code.

Self-contained and **Streamlit-Community-Cloud ready** — `streamlit_app.py` and
`requirements.txt` at the repo root, no arguments.

```
practice-platform/
├── streamlit_app.py          # the app (entry point)
├── sandbox.py                # runtime helpers injected into every Run (mock/real model + embeddings)
├── requirements.txt          # app + full LangChain stack  <-- MUST be at repo root
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
  `import langchain_community…` now works.
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
  MODE = "mock"   # or "real", from the sidebar
  ```

---

## Mock mode vs Real LLM mode

Chosen in the sidebar. **The LangChain pipeline is identical in both** — loaders,
splitters, the vector store, retrievers, prompts, chains and graphs are all real.
Only the model and embeddings implementations swap.

| | 🧪 **Mock mode** | 🔌 **Real LLM mode** |
|---|---|---|
| API key | **not required** | `OPENAI_API_KEY` **required** |
| Network | none | calls OpenAI |
| `get_chat_model(MODE)` | a local `BaseChatModel` subclass that answers from the retrieved `Context:` block, or refuses | `langchain_openai.ChatOpenAI(model="gpt-4o-mini")` |
| `get_embeddings(MODE)` | `langchain_core…DeterministicFakeEmbedding` | `langchain_openai.OpenAIEmbeddings(model="text-embedding-3-small")` |
| Cost | free | billed to your OpenAI account |

Set the key for Real mode:

- **Local:** `export OPENAI_API_KEY=sk-…` (or a `.env` file — `python-dotenv` is installed)
- **Cloud:** *Manage app → Settings → Secrets* → `OPENAI_API_KEY = "sk-…"`

---

## Run locally

```bash
cd practice-platform
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt    # installs into THIS venv — the one Streamlit will use
streamlit run streamlit_app.py
```

Mock mode works immediately. For Real mode, set `OPENAI_API_KEY` first.

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
3. *Advanced settings* → Python **3.12** → **Deploy**. First build installs the
   LangChain stack (~2–3 min).
4. (Optional) add `OPENAI_API_KEY` in *Settings → Secrets* to enable Real mode.

Open a specific lab with `?lab=<folder-name>` in the URL.

### Deploy errors → fixes

| Log message | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'yaml'` / `'langchain_community'` … | `requirements.txt` isn't at the repo root, or the build didn't finish — it must sit next to `streamlit_app.py` at the top level; redeploy / "Reboot app". |
| `No content found` / `FileNotFoundError: .../content/...` | `content/` wasn't committed, or `streamlit_app.py` isn't at the repo root. |
| Run says **"Cannot Run — packages missing"** | The app's env is missing that package. It's in `requirements.txt`; *Manage app → Reboot app* to reinstall. |
| Run in Real mode: `AuthenticationError` / "needs OPENAI_API_KEY" | Add the key in *Settings → Secrets*, or use Mock mode. |
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
