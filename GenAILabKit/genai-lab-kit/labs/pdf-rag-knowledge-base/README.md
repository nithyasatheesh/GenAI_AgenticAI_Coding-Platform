# PDF-Based Knowledge Base RAG System — Guided Lab

A hands-on lab: build a Retrieval-Augmented Generation (RAG) app that answers
questions about a PDF using **only** that document's content.

```
PDF → PyPDFLoader → chunking (1000/200) → text-embedding-3-small
    → ChromaDB → retriever (k=3) → grounded prompt → gpt-4o-mini → answer + source pages
```

## Participant experience

**Log in to the VM → open Jupyter or VS Code → open the participant notebook → complete the `# TODO` cells → run → validate.**

No participant setup: no `pip install`, no Jupyter/VS Code install, no API key creation. The VM vendor does all of that (see [`../../vm-provisioning/`](../../vm-provisioning/)).

## Folder map

| Path | What it is |
|------|------------|
| `00_START_HERE.md` | First thing the participant reads |
| `01_TASK_GUIDE/TASKS.md` | The 5 tasks, hints, expected output, checklist |
| `02_STARTER_CODE/participant_notebook.ipynb` | Problem notebook with `# TODO` cells |
| `02_STARTER_CODE/rag_app.py` | Task 5 starter (stub with `# TODO`s) |
| `03_SOLUTION_GUIDE/solution_notebook.ipynb` | Full reference implementation — **trainer only** |
| `03_SOLUTION_GUIDE/rag_app.py` | Reference interactive app |
| `04_DATA/sample_knowledge_base.pdf` | The knowledge source (synthetic HR handbook) |
| `04_DATA/RAG_Question_Set.pdf` | 20 validation questions — **not** a source document |
| `05_CONFIG/.env.example` | Copy to `.env`; the vendor fills in the key |
| `05_CONFIG/requirements.txt` | Exact packages the VM must preinstall |
| `06_REFERENCE/architecture.md` | Annotated pipeline diagram + design notes |
| `scripts/setup_check.py` | Preflight: packages + key + data + network |
| `scripts/validate_solution.py` | Automated grader against the question set |
| `chroma_db/` | Vector store working dir (git-ignored) |

## Quick start (participant)

```bash
cd 02_STARTER_CODE
jupyter notebook participant_notebook.ipynb      # or: code .
```

Run **Task 0** first — it verifies the environment. Then work Tasks 1–5 in order.

## Quick start (trainer / QA)

```bash
python scripts/setup_check.py        # environment is healthy
python scripts/validate_solution.py  # solution passes grounded + negative tests
```

## Success criteria

- Chunking is 1000 / 200; retrieval `k=3`; `gpt-4o-mini` at `temperature=0`.
- Answers use only retrieved context and list de-duplicated source pages.
- Out-of-context questions return exactly:
  `I could not find the answer in the provided document.`
