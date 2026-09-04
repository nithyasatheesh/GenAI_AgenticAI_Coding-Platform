# <Lab Title> — Guided Lab

<One paragraph: what the participant builds and why.>

```
<pipeline: A -> B -> C -> ...>
```

## Participant experience

**Log in to the VM → open Jupyter or VS Code → open the participant notebook → complete the `# TODO` cells → run → validate.**

No participant setup — the VM vendor preinstalls everything and configures secrets.

## Folder map

| Path | What it is |
|------|------------|
| `00_START_HERE.md` | First thing the participant reads |
| `01_TASK_GUIDE/TASKS.md` | Tasks, hints, expected output, checklist |
| `02_STARTER_CODE/` | Participant notebook + starter scripts (`# TODO`) |
| `03_SOLUTION_GUIDE/` | Full reference — **trainer only** |
| `04_DATA/` | Supplied datasets |
| `05_CONFIG/` | `.env.example`, `requirements.txt` |
| `06_REFERENCE/` | Architecture diagram + design notes |
| `scripts/setup_check.py` | Preflight: packages + secrets + data |
| `scripts/validate_solution.py` | Automated grader |

## Quick start

```bash
python scripts/setup_check.py
cd 02_STARTER_CODE && jupyter notebook participant_notebook.ipynb
```

## Success criteria

<bullet list of what must be true for the lab to be "done">
