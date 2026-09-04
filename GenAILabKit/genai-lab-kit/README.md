# GenAI Lab Kit

A repeatable structure for authoring and delivering **guided GenAI and Agentic-AI
coding labs** on a preconfigured-VM platform (Jupyter / VS Code).

Every lab follows the same delivery model:

> **Log in to VM → open Jupyter/VS Code → open the participant notebook → type/copy code → run → validate.**

No participant setup — the VM vendor preinstalls packages and configures secrets.

## What's in here

| Path | Purpose |
|------|---------|
| [`PLATFORM_SPEC.md`](PLATFORM_SPEC.md) | The contract every lab follows (layout, `lab.yaml` schema, script contracts, security). |
| [`AUTHORING_GUIDE.md`](AUTHORING_GUIDE.md) | Step-by-step for writing a new lab, with a worked Agentic-AI example. |
| [`lab-template/`](lab-template/) | Skeleton copied by the scaffolder to start a new lab. |
| [`labs/`](labs/) | The actual labs. |
| [`labs/pdf-rag-knowledge-base/`](labs/pdf-rag-knowledge-base/) | **Reference lab, fully built** — PDF → RAG → grounded answers. |
| [`tools/new_lab.py`](tools/new_lab.py) | `python tools/new_lab.py <id> --title "..." --track ...` |
| [`tools/aggregate_requirements.py`](tools/aggregate_requirements.py) | Merges all labs' deps into one VM requirement set. |
| [`vm-provisioning/`](vm-provisioning/) | VM requirements doc, `provision.sh`, aggregated `requirements.txt`. |

## Add a lab

```bash
python tools/new_lab.py my-lab-id --title "My Lab" --track agentic-ai
# fill lab.yaml, add data, write the 2 notebooks, wire the 2 scripts
python tools/aggregate_requirements.py
```

See `AUTHORING_GUIDE.md`.

## Build a VM image

```bash
python tools/aggregate_requirements.py          # refresh vm-provisioning/requirements.txt
sudo ./vm-provisioning/provision.sh             # Ubuntu 22.04
# per lab: cp 05_CONFIG/.env.example 05_CONFIG/.env  (add the vendor key)
#          python scripts/setup_check.py --live
#          python scripts/validate_solution.py
# then REMOVE every labs/*/03_SOLUTION_GUIDE/ from the participant image
```

Details in [`vm-provisioning/VM_REQUIREMENTS.md`](vm-provisioning/VM_REQUIREMENTS.md).

## The reference lab

[`labs/pdf-rag-knowledge-base/`](labs/pdf-rag-knowledge-base/) — a complete
beginner RAG lab:

```
PDF → PyPDFLoader → chunk(1000/200) → text-embedding-3-small
    → ChromaDB → retriever(k=3) → grounded prompt → gpt-4o-mini → answer + pages
```

5 tasks, participant + solution notebooks, starter + reference `rag_app.py`,
preflight and autograder scripts, architecture reference, and the two datasets.
Use it as the pattern for every new lab.
