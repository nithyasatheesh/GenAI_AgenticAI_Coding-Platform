# Authoring Guide — writing a new lab

Follow this to add a GenAI or Agentic-AI lab that the platform can host with zero
custom work. Read `PLATFORM_SPEC.md` first for the contract.

## 1. Scaffold

```bash
python tools/new_lab.py tool-calling-weather-agent \
  --title "Tool-Calling Weather Agent" --track agentic-ai --difficulty intermediate
```

Creates `labs/tool-calling-weather-agent/` from `lab-template/`.

## 2. Fill `lab.yaml`

Every `<...>` placeholder. `parameters` and `validation` are the important ones —
they define what "done" means and what the grader checks. Keep `id` == folder name.

## 3. Add data

Drop synthetic datasets into `04_DATA/` and list them under `data:` in `lab.yaml`.
No real personal data. If a lab needs a validation set, keep it **separate** from
the knowledge source and say so in the file.

## 4. Write the task guide

`01_TASK_GUIDE/TASKS.md`: 4–6 tasks, each with

- **Goal** — one line.
- **Do** — numbered concrete steps.
- **Hints** — exactly three, progressive (points at the tool → narrows it → almost
  the answer).
- **Expected** — what the participant should see.

End with the **Final checklist** (one box per verifiable claim).

## 5. Write the two notebooks

Generate them with a small Python script (see
`labs/pdf-rag-knowledge-base` — its notebooks were produced by a generator so the
participant and solution stay in lock-step). Rules:

- **Cell 0 is always Task 0**: `%run ../scripts/setup_check.py`.
- Participant cells contain `# TODO` and nothing that gives the answer away.
- Solution notebook mirrors the same task order with complete, runnable code.
- Relative paths assume the notebook runs from its own folder
  (`02_STARTER_CODE/` or `03_SOLUTION_GUIDE/`), so data is `../04_DATA/...`.
- LLM calls: `temperature=0`, model pinned from `lab.yaml`.

## 6. Wire the scripts

- `scripts/setup_check.py` — set `REQUIRED_IMPORTS`, `REQUIRED_ENV`, `DATA_FILES`.
- `scripts/validate_solution.py` — import the reference from `03_SOLUTION_GUIDE/`,
  implement `checks_offline()` and `checks_live()`. Assert the promises: correct
  answers on positive cases, the exact refusal/format on edge cases, output shape.

## 7. Draw the architecture

`06_REFERENCE/architecture.md`: an ASCII block diagram annotated with the class /
model / parameter at each stage, a "why each choice" table, the grader contracts,
and common pitfalls.

## 8. Update the VM image

```bash
python tools/aggregate_requirements.py        # merges into vm-provisioning/requirements.txt
```

## 9. Self-check before handing off

```bash
cd labs/<lab-id>
python scripts/setup_check.py            # offline part green
python scripts/validate_solution.py --offline
# then, with a key set:
python scripts/setup_check.py --live
python scripts/validate_solution.py
```

Also open both notebooks top-to-bottom in Jupyter and run every cell.

## 10. Worked example — an Agentic-AI lab

**Lab:** "Tool-Calling Weather Agent" (`track: agentic-ai`, intermediate, ~90 min).

| Task | Area | Goal |
|------|------|------|
| 1 | Tool schema | Define two tools (`get_weather`, `calculator`) with JSON-Schema args. |
| 2 | Single tool call | Bind tools to `gpt-4o-mini`; make the model emit one tool call; execute it; return the result. |
| 3 | ReAct loop | Loop tool-call → observation → next step until the model answers; cap iterations. |
| 4 | Planning + guardrail | Add a planning step and refuse out-of-scope requests. |
| 5 | Interactive agent | Combine into `agent_app.py` with a chat loop and a transcript of tool calls. |

- `parameters`: `max_iterations: 6`, `temperature: 0`, `refusal_text: "I can only help with weather and arithmetic."`
- `validation`: a weather question calls `get_weather` exactly once and answers;
  "what's 18% of 240" routes to `calculator`; "book me a flight" hits the refusal;
  the loop never exceeds `max_iterations`.
- Same folder layout, same two scripts, same delivery model.
