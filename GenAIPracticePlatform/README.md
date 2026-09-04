# GenAI Lab — Practice Platform

Interactive practice UI for guided GenAI / Agentic-AI labs. Per task: the question,
progressive hints, a code editor, a reveal-solution toggle, and an auto-scored
**Check**. A **Score** page totals it up.

This folder is **self-contained and Streamlit-Community-Cloud ready** — no arguments,
no external paths, `requirements.txt` at the root.

```
practice-platform/
├── streamlit_app.py      # the app (entry point)
├── requirements.txt      # streamlit, pyyaml   <-- MUST be at repo root
├── .gitignore
└── content/
    └── pdf-rag-knowledge-base/
        └── practice.yaml # one lab's tasks: prompt / hints / starter / solution / checks
```

## Run locally

```bash
cd practice-platform
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Opens at <http://localhost:8501>.

## Deploy to Streamlit Community Cloud (from GitHub)

1. Put **the contents of this folder at the repo root** (so `streamlit_app.py` and
   `requirements.txt` are top-level — not inside another folder):

   ```bash
   cd practice-platform
   git init
   git add .
   git commit -m "GenAI Lab practice platform"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```

2. <https://share.streamlit.io> → **Create app** → **Deploy a public app from GitHub**.
3. Repo = yours, branch = `main`, **Main file path = `streamlit_app.py`**.
4. *Advanced settings* → Python **3.12**.
5. **Deploy.** First build installs `streamlit` + `pyyaml` (~1 min).

Open a specific lab with `?lab=<folder-name>` in the URL.

### If the deploy fails — match the message

| Message in the Streamlit "Manage app" logs | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'yaml'` | `requirements.txt` isn't at the repo root, or is missing `pyyaml`. It must sit next to `streamlit_app.py` at the **top level** of the repo. |
| `No content found` / `FileNotFoundError: .../content/...` | The `content/` folder wasn't committed, or `streamlit_app.py` isn't at the repo root. Keep the layout above intact. |
| `Error: Main module ... not found` | Main file path must be exactly `streamlit_app.py` (no folder prefix) with this layout. |
| `git push` → `Authentication failed` / `Permission denied` | Use a GitHub Personal Access Token (or `gh auth login` / GitHub Desktop), not your account password. |
| `src refspec main does not match any` | You didn't commit — run the `git add . && git commit` step first. |
| `Updates were rejected` on push | The GitHub repo already had commits. Create a fresh empty repo (no README), or `git pull --rebase origin main` then push. |
| Build OK but page says **Reveal / Check** work and **Run** shows `ModuleNotFoundError` | Expected. This platform only needs `streamlit` + `pyyaml`. **Run** executes learner code and would need the lab's own libraries (`langchain`, …) + an API key — that belongs in the VM/notebook, not this public demo. Add them to `requirements.txt` only if you want Run to work here too. |

## Add another lab

Create `content/<new-lab-id>/practice.yaml` with the same shape (see
`content/pdf-rag-knowledge-base/practice.yaml`). It appears in the sidebar
automatically. Each task needs: `title`, `prompt`, `hints[]`, `starter`,
`solution`, `checks[]` (`{pattern, points, desc}` — regex over the learner's code).

## What this is / isn't

- **Is:** a hosted practice-and-self-check UI for lab content.
- **Isn't:** the VM coding environment. Real execution against OpenAI/ChromaDB
  happens in the lab VM or notebook. See the full `genai-lab-kit/` for the
  notebooks, VM provisioning, `grade_submission.py` (0–100 grader) and
  `validate_solution.py` (vendor QA).
