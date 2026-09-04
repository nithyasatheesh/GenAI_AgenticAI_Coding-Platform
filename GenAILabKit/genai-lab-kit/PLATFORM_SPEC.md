# Platform Spec — GenAI Lab Kit

The contract every lab in this kit follows so the delivery platform (VM image +
Jupyter/VS Code) can host any of them the same way.

## 1. Delivery model

> **Log in to VM → open Jupyter/VS Code → open participant notebook → type/copy code → run → validate.**

- **No participant setup.** No `pip install`, no IDE install, no key creation, no
  environment config. The vendor does all of it and validates it
  (`vm-provisioning/VM_REQUIREMENTS.md`).
- **Two notebooks per lab.** A participant notebook (problem + `# TODO` cells +
  hints + expected output + checklist) and a *separate* solution notebook
  (trainer only, released after the session).
- **Deterministic.** LLM calls use `temperature=0`; any grader depends only on
  fixed parameters declared in `lab.yaml`.

## 2. Canonical lab layout

```
labs/<lab-id>/
├── lab.yaml                     # manifest (schema below)
├── README.md                    # overview + folder map
├── 00_START_HERE.md             # participant's first read
├── 01_TASK_GUIDE/TASKS.md       # tasks, 3 progressive hints each, expected output, checklist
├── 02_STARTER_CODE/
│   ├── participant_notebook.ipynb
│   └── <starter scripts with # TODO>
├── 03_SOLUTION_GUIDE/           # TRAINER ONLY - excluded from participant image
│   ├── solution_notebook.ipynb
│   └── <reference scripts>
├── 04_DATA/                     # supplied datasets (the only knowledge sources)
├── 05_CONFIG/
│   ├── .env.example             # real .env is vendor-filled, git-ignored
│   └── requirements.txt         # exact packages for this lab
├── 06_REFERENCE/architecture.md # annotated pipeline diagram + design rationale
├── scripts/
│   ├── setup_check.py           # preflight: packages + secrets + data (+ --live)
│   └── validate_solution.py     # automated grader (+ --offline)
└── chroma_db/ (or other working dirs)   # git-ignored, ships empty
```

`id` in `lab.yaml` **must equal** the folder name.

## 3. `lab.yaml` schema (informal)

| Key | Meaning |
|-----|---------|
| `id` | kebab-case, == folder name |
| `title` | human-readable |
| `track` | `genai` or `agentic-ai` |
| `difficulty` | `beginner` / `intermediate` / `advanced` |
| `duration_minutes` | integer estimate |
| `summary` | 2–3 sentences |
| `stack` | `language`, `python`, `ide[]`, `services[]` |
| `models` | `chat`, `embeddings` (omit if not an LLM lab) |
| `parameters` | fixed knobs graders rely on (chunk size, k, temperature, exact strings…) |
| `entrypoints` | notebook + app paths |
| `data[]` | dataset paths under `04_DATA/` |
| `config` | `env_example`, `requirements`, `secrets[]` (`name`, `managed_by`) |
| `scripts` | `preflight`, `validate` |
| `tasks[]` | `id`, `area`, `goal` — mirrors `01_TASK_GUIDE/TASKS.md` |
| `validation` | prose describing what "correct" means / what the grader asserts |

## 4. Script contracts

**`scripts/setup_check.py`**
- Verifies importable packages, required env vars (loads `05_CONFIG/.env`), and
  every file in `04_DATA/`.
- `--live` adds one minimal paid API call to prove the key works.
- Exit `0` = ready, `1` = something missing. Resolves paths from its own location.

**`scripts/validate_solution.py`**
- Imports the reference implementation from `03_SOLUTION_GUIDE/` and asserts the
  behaviours the lab promises (positive answers, refusals, output shapes…).
- `--offline` runs only what needs no paid API (parsing, wiring, imports).
- Exit `0` = all pass, `1` = failures, `2` = environment not ready.

## 5. Security rules

- The real `.env` / API key is **vendor-managed**, git-ignored, and never enters
  a participant solution-sharing area.
- `03_SOLUTION_GUIDE/` is stripped from the participant VM image.
- Datasets are synthetic; no real personal data.

## 6. Tracks

- **`genai`** — prompting, RAG, structured output, evaluation, embeddings, summarisation.
- **`agentic-ai`** — tool use, planning, ReAct, multi-agent, memory, MCP, guardrails.

Both use the identical layout, scripts, and delivery model. The only differences
are the notebook content and `lab.yaml`.
