# Start Here

Welcome. You will build a **PDF Knowledge Base RAG system** in about 90 minutes.

## 1. What you are building

An app where you ask a question in plain English and get an answer drawn **only**
from a supplied PDF — with the page numbers it came from. If the PDF does not
contain the answer, the app says so instead of guessing.

## 2. Your environment is ready

This VM already has Python, Jupyter, VS Code, every package, and the OpenAI API
key configured. **Do not run `pip install` or create an API key.**

## 3. What to do

1. Open a terminal and run the preflight check:
   ```bash
   python scripts/setup_check.py
   ```
   You should see `ALL CHECKS PASSED`. If not, tell your instructor.

2. Open the participant notebook:
   ```bash
   cd 02_STARTER_CODE
   jupyter notebook participant_notebook.ipynb
   ```
   (or open the folder in VS Code and open the `.ipynb`).

3. Run **Task 0** (the first code cell), then complete Tasks 1–5 in order.
   Each task in [`01_TASK_GUIDE/TASKS.md`](01_TASK_GUIDE/TASKS.md) has a goal,
   hints, and the output you should expect.

4. For **Task 5**, complete [`02_STARTER_CODE/rag_app.py`](02_STARTER_CODE/rag_app.py)
   and run it from a terminal.

5. Finish by running:
   ```bash
   python scripts/validate_solution.py
   ```

## 4. Rules of the lab

- Use only `04_DATA/sample_knowledge_base.pdf` as the knowledge source.
- `04_DATA/RAG_Question_Set.pdf` is for testing — never feed it to the RAG system.
- Keep the required settings: chunk size **1000**, overlap **200**, `k=3`,
  `gpt-4o-mini`, `temperature=0`.

## 5. If you get stuck

Each task has three progressive hints. The full solution is held by your
instructor and released after the session.
