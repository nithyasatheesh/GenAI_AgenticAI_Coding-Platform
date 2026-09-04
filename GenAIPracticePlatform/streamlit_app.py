"""GenAI Lab - interactive practice platform (Streamlit Community Cloud ready).

Per task: prompt + progressive hints + code editor + reveal-solution + auto-scored
Check, plus a Score page. Content is data - add folders under ./content/<lab>/ each
holding a practice.yaml.

Deploy: repo root = this folder, main file = streamlit_app.py, requirements.txt is
next to this file. Nothing else required.
"""
from __future__ import annotations

import contextlib
import io
import re
import traceback
from pathlib import Path

import streamlit as st

try:
    import yaml
except ModuleNotFoundError:
    st.set_page_config(page_title="Lab Practice", page_icon="🧪")
    st.error(
        "**PyYAML is missing.** Add a line `pyyaml` to `requirements.txt` at the "
        "repo root, commit, and let Streamlit rebuild."
    )
    st.stop()

HERE = Path(__file__).resolve().parent
CONTENT = HERE / "content"

st.set_page_config(page_title="GenAI Lab Practice", page_icon="🧪", layout="wide")


# --------------------------------------------------------------------------- #
#  content loading                                                             #
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def list_labs() -> list[str]:
    if not CONTENT.is_dir():
        return []
    return sorted(p.name for p in CONTENT.iterdir()
                  if (p / "practice.yaml").is_file())


@st.cache_data(show_spinner=False)
def load_lab(lab_id: str) -> dict:
    return yaml.safe_load((CONTENT / lab_id / "practice.yaml").read_text("utf-8"))


# --------------------------------------------------------------------------- #
#  grading                                                                     #
# --------------------------------------------------------------------------- #
def code_only(src: str) -> str:
    """Strip # comments so the rubric grades real code, not the `# TODO` hints.
    Triple-quoted strings (e.g. a prompt template) are preserved."""
    out, in_str, q = [], False, ""
    for line in src.splitlines():
        buf, i = "", 0
        while i < len(line):
            chunk = line[i:i + 3]
            if not in_str and chunk in ('"""', "'''"):
                in_str, q, buf, i = True, chunk, buf + chunk, i + 3
                continue
            if in_str and line[i:i + 3] == q:
                in_str, buf, i = False, buf + q, i + 3
                continue
            if not in_str and line[i] == "#":
                break
            buf += line[i]
            i += 1
        out.append(buf)
    return "\n".join(out)


def check(code: str, checks: list[dict]) -> list[tuple[str, bool, int, int]]:
    clean = code_only(code)
    rows = []
    for c in checks:
        ok = bool(re.search(c["pattern"], clean, re.I | re.S))
        rows.append((c["desc"], ok, c["points"] if ok else 0, c["points"]))
    return rows


def run_accumulated(spec: dict, upto_id: int) -> tuple[str, str]:
    parts = []
    for t in spec["tasks"]:
        parts.append(f"# ===== Task {t['id']} =====\n"
                     + st.session_state.get(f"code_{t['id']}", t["starter"]))
        if t["id"] == upto_id:
            break
    source = "\n\n".join(parts)
    demo = iter(["What is the standard notice period?", "exit", "exit", "exit"])
    ns = {"__name__": "__practice__", "input": lambda *_a: next(demo, "exit")}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(compile(source, "<practice>", "exec"), ns)  # noqa: S102
        return buf.getvalue(), ""
    except Exception:
        return buf.getvalue(), traceback.format_exc(limit=3)


# --------------------------------------------------------------------------- #
#  UI                                                                          #
# --------------------------------------------------------------------------- #
def main() -> None:
    labs = list_labs()
    if not labs:
        st.error("No content found. Add `content/<lab>/practice.yaml` to the repo.")
        st.stop()

    qp_lab = st.query_params.get("lab")
    default_idx = labs.index(qp_lab) if qp_lab in labs else 0
    with st.sidebar:
        lab_id = st.selectbox("Lab", labs, index=default_idx)
        spec = load_lab(lab_id)
        st.title(spec.get("title", lab_id))
        st.caption(lab_id)
        tasks = spec["tasks"]
        labels = [f"Task {t['id']} · {t['title']}" for t in tasks] + ["★ Score"]
        choice = st.radio("Go to", labels, label_visibility="collapsed")
        if spec.get("notes"):
            st.info(spec["notes"])
        st.caption("Tip: `?lab=<id>` in the URL opens a specific lab.")

    if choice == "★ Score":
        render_score(spec)
    else:
        render_task(spec, tasks[labels.index(choice)])


def render_score(spec: dict) -> None:
    st.title("Your score")
    got = possible = 0
    for t in spec["tasks"]:
        rows = st.session_state.get(f"result_{t['id']}")
        revealed = st.session_state.get(f"revealed_{t['id']}", False)
        tmax = sum(c["points"] for c in t["checks"])
        tgot = sum(r[2] for r in rows) if rows else 0
        possible += tmax
        got += tgot
        state = ("— not attempted" if rows is None
                 else f"{tgot}/{tmax}" + ("  · solution viewed" if revealed else ""))
        st.write(f"**Task {t['id']} — {t['title']}**  ·  {state}")
    pct = round(100 * got / possible) if possible else 0
    band = ("Excellent" if pct >= 85 else "Pass" if pct >= 70
            else "Needs work" if pct >= 50 else "Incomplete")
    st.divider()
    st.subheader(f"{got} / {possible}   ({pct}%)   —   {band}")
    st.progress(pct / 100)


def render_task(spec: dict, t: dict) -> None:
    tid = t["id"]
    ckey, hkey, rkey = f"code_{tid}", f"hints_{tid}", f"revealed_{tid}"
    st.session_state.setdefault(ckey, t["starter"])
    st.session_state.setdefault(hkey, 0)

    st.title(f"Task {tid} — {t['title']}")
    st.markdown(t["prompt"])

    left, right = st.columns([3, 2])
    with left:
        st.markdown("**Your code**")
        code = st.text_area("code", key=ckey, height=340, label_visibility="collapsed")
        c1, c2, c3, c4 = st.columns(4)
        do_check = c1.button("✓ Check", type="primary", key=f"chk_{tid}")
        do_run = c2.button("▶ Run", key=f"run_{tid}",
                           help="Executes Task 1..N in a fresh namespace. "
                                "Needs the lab's packages installed.")
        if c3.button("💡 Hint", key=f"hint_{tid}"):
            st.session_state[hkey] = min(len(t["hints"]), st.session_state[hkey] + 1)
        if c4.button("↺ Reset", key=f"rst_{tid}"):
            st.session_state[ckey] = t["starter"]
            st.session_state.pop(f"result_{tid}", None)
            st.rerun()

        if do_check:
            st.session_state[f"result_{tid}"] = check(code, t["checks"])
        rows = st.session_state.get(f"result_{tid}")
        if rows:
            got, mx = sum(r[2] for r in rows), sum(r[3] for r in rows)
            st.markdown(f"**Check: {got} / {mx}**")
            for desc, ok, pts, pmax in rows:
                st.markdown(f"{'✅' if ok else '❌'} {desc} — {pts}/{pmax}")

        if do_run:
            with st.spinner("Running…"):
                out, err = run_accumulated(spec, tid)
            if out:
                st.markdown("**Output**")
                st.code(out or "(no output)", language="text")
            if err:
                st.markdown("**Error**")
                st.code(err, language="text")
                if "ModuleNotFoundError" in err:
                    st.info("This deployment doesn't have the lab's libraries "
                            "installed, so **Run** can't execute the pipeline. "
                            "**Check** and **Reveal solution** work without them — "
                            "run the code for real in the VM / notebook.")

    with right:
        shown = st.session_state[hkey]
        st.markdown(f"**Hints** ({shown}/{len(t['hints'])})")
        for h in t["hints"][:shown]:
            st.markdown(f"- {h}")
        if shown < len(t["hints"]):
            st.caption("Press **💡 Hint** for the next one.")
        st.divider()
        if st.checkbox("Reveal solution code", key=f"revchk_{tid}",
                       value=st.session_state.get(rkey, False)):
            st.session_state[rkey] = True
            st.code(t["solution"], language="python")
            if st.button("Copy into my editor", key=f"cpy_{tid}"):
                st.session_state[ckey] = t["solution"]
                st.rerun()
        else:
            st.caption("Try it yourself first — revealing is flagged on the Score page.")


if __name__ == "__main__":
    main()
