"""GenAI Lab - interactive practice platform (Streamlit Community Cloud ready).

Per task: prompt + progressive hints + code editor + reveal-solution + auto-scored
Check + a REAL "Run" that executes the learner's code in this app's Python
interpreter (see README "Where learner code runs").

Content is data: add folders under ./content/<lab>/ each with a practice.yaml.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import re
import sys
import traceback
from pathlib import Path

import streamlit as st

try:
    import yaml
except ModuleNotFoundError:
    st.set_page_config(page_title="Lab Practice", page_icon="🧪")
    st.error("**PyYAML is missing.** Add `pyyaml` to `requirements.txt` at the repo "
             "root, commit, and let Streamlit rebuild.")
    st.stop()

HERE = Path(__file__).resolve().parent
CONTENT = HERE / "content"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))          # so learner code can `import sandbox`

# make a Streamlit-Cloud secret visible to os.environ (Real LLM mode)
# surface Streamlit-Cloud secrets to os.environ for the real-LLM modes
for _sec in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_MODEL", "ANTHROPIC_MODEL"):
    try:
        if _sec in st.secrets and not os.environ.get(_sec):
            os.environ[_sec] = str(st.secrets[_sec])
    except Exception:
        pass

st.set_page_config(page_title="GenAI Lab Practice", page_icon="🧪", layout="wide")

# canonical pip name for an import name (for the "missing package" message)
PIP_NAME = {
    "langchain_core": "langchain-core", "langchain_community": "langchain-community",
    "langchain_text_splitters": "langchain-text-splitters",
    "langchain_openai": "langchain-openai", "langchain_anthropic": "langchain-anthropic",
    "langgraph": "langgraph", "pypdf": "pypdf",
}

# mode -> (extra import needed to Run, env var holding the key)
MODE_REQUIRES = {
    "openai": ("langchain_openai", "OPENAI_API_KEY"),
    "claude": ("langchain_anthropic", "ANTHROPIC_API_KEY"),
}


# --------------------------------------------------------------------------- #
#  content                                                                     #
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def list_labs() -> list[str]:
    if not CONTENT.is_dir():
        return []
    return sorted(p.name for p in CONTENT.iterdir() if (p / "practice.yaml").is_file())


@st.cache_data(show_spinner=False)
def load_lab(lab_id: str) -> dict:
    return yaml.safe_load((CONTENT / lab_id / "practice.yaml").read_text("utf-8"))


# --------------------------------------------------------------------------- #
#  grading (Check)                                                             #
# --------------------------------------------------------------------------- #
def code_only(src: str) -> str:
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
    return [(c["desc"], bool(re.search(c["pattern"], clean, re.I | re.S)),
             c["points"] if re.search(c["pattern"], clean, re.I | re.S) else 0,
             c["points"]) for c in checks]


# --------------------------------------------------------------------------- #
#  Run - REAL execution in this interpreter                                    #
# --------------------------------------------------------------------------- #
def dependency_report(requires: list[str], mode: str) -> list[str]:
    need = list(requires or [])
    extra = MODE_REQUIRES.get(mode, (None, None))[0]
    if extra and extra not in need:
        need.append(extra)
    return [m for m in need if importlib.util.find_spec(m) is None]


def preamble(mode: str) -> str:
    return (
        "import os as _os, sys as _sys\n"
        f"_sys.path.insert(0, r'{HERE}')\n"
        f"_os.environ['SANDBOX_MODE'] = '{mode}'\n"
        "import sandbox\n"
        "from sandbox import (get_chat_model, get_embeddings, load_sample_docs,\n"
        "                     make_vectorstore, SAMPLE_PDF)\n"
        f"MODE = '{mode}'\n"
        "# ---------------- your code below ----------------\n"
    )


def run_accumulated(spec: dict, upto_id: int, mode: str) -> tuple[str, str]:
    parts = []
    for t in spec["tasks"]:
        parts.append(f"# ===== Task {t['id']} =====\n"
                     + st.session_state.get(f"code_{t['id']}", t["starter"]))
        if t["id"] == upto_id:
            break
    source = preamble(mode) + "\n\n".join(parts)

    demo = iter(["What is the standard notice period for regular full-time employees?",
                 "How many casual leave days are provided?", "exit", "exit", "exit"])
    ns = {"__name__": "__practice__", "input": lambda *_a: next(demo, "exit")}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(compile(source, "<practice>", "exec"), ns)  # noqa: S102
        return buf.getvalue(), ""
    except Exception:
        return buf.getvalue(), traceback.format_exc()


# --------------------------------------------------------------------------- #
#  UI                                                                          #
# --------------------------------------------------------------------------- #
def main() -> None:
    labs = list_labs()
    if not labs:
        st.error("No content found. Add `content/<lab>/practice.yaml`.")
        st.stop()

    qp = st.query_params.get("lab")
    with st.sidebar:
        lab_id = st.selectbox("Lab", labs, index=labs.index(qp) if qp in labs else 0)
        spec = load_lab(lab_id)
        st.title(spec.get("title", lab_id))

        st.divider()
        _MODE_LABELS = {
            "🧪 Mock — no API key": "mock",
            "🔷 OpenAI — OPENAI_API_KEY": "openai",
            "🟣 Claude — ANTHROPIC_API_KEY": "claude",
        }
        pick = st.radio("LLM mode", list(_MODE_LABELS),
                        help="Mock: local model + embeddings, fully offline. "
                             "OpenAI: langchain-openai ChatOpenAI + embeddings. "
                             "Claude: langchain-anthropic ChatAnthropic (generation only "
                             "— Anthropic has no embeddings API).")
        mode = _MODE_LABELS[pick]
        if mode == "mock":
            st.caption("✅ Offline. The LangChain **pipeline is real**; only the model "
                       "and embeddings are local stand-ins.")
        else:
            pkg, envk = MODE_REQUIRES[mode]
            has_key = os.environ.get(envk, "").startswith(("sk-", "sk-ant-"))
            if importlib.util.find_spec(pkg) is None:
                st.caption(f"⚠ `{PIP_NAME[pkg]}` not installed — uncomment it in "
                           f"`requirements.txt` and redeploy.")
            elif has_key:
                st.caption(f"✅ `{envk}` detected — real "
                           f"{'OpenAI' if mode == 'openai' else 'Claude'} calls will be made"
                           + ("." if mode == "openai"
                              else "; retrieval still uses local embeddings."))
            else:
                st.caption(f"⚠ No `{envk}`. Set it in **App → Settings → Secrets** "
                           f"(cloud) or your environment (local), or use Mock mode.")
        st.session_state["mode"] = mode

        st.divider()
        tasks = spec["tasks"]
        labels = [f"Task {t['id']} · {t['title']}" for t in tasks] + ["★ Score"]
        choice = st.radio("Go to", labels, label_visibility="collapsed")
        if spec.get("notes"):
            st.info(spec["notes"])

    if choice == "★ Score":
        render_score(spec)
    else:
        render_task(spec, tasks[labels.index(choice)], mode)


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
        state = ("— not attempted" if rows is None else
                 f"{tgot}/{tmax}" + ("  · solution viewed" if revealed else ""))
        st.write(f"**Task {t['id']} — {t['title']}**  ·  {state}")
    pct = round(100 * got / possible) if possible else 0
    band = ("Excellent" if pct >= 85 else "Pass" if pct >= 70
            else "Needs work" if pct >= 50 else "Incomplete")
    st.divider()
    st.subheader(f"{got} / {possible}   ({pct}%)   —   {band}")
    st.progress(pct / 100)


def render_task(spec: dict, t: dict, mode: str) -> None:
    tid = t["id"]
    ckey, hkey, rkey = f"code_{tid}", f"hints_{tid}", f"revealed_{tid}"
    st.session_state.setdefault(ckey, t["starter"])
    st.session_state.setdefault(hkey, 0)

    # apply deferred editor edits BEFORE the text_area is instantiated this run
    if st.session_state.pop(f"_reset_{tid}", False):
        st.session_state[ckey] = t["starter"]
    if st.session_state.pop(f"_loadsol_{tid}", False):
        st.session_state[ckey] = t["solution"]

    st.title(f"Task {tid} — {t['title']}")
    st.markdown(t["prompt"])

    left, right = st.columns([3, 2])
    with left:
        st.markdown("**Your code**")
        code = st.text_area("code", key=ckey, height=340, label_visibility="collapsed")
        c1, c2, c3, c4 = st.columns(4)
        do_check = c1.button("✓ Check", type="primary", key=f"chk_{tid}")
        do_run = c2.button(f"▶ Run ({mode})", key=f"run_{tid}",
                           help="Executes Task 1..N in this app's Python interpreter.")
        if c3.button("💡 Hint", key=f"hint_{tid}"):
            st.session_state[hkey] = min(len(t["hints"]), st.session_state[hkey] + 1)
        if c4.button("↺ Reset", key=f"rst_{tid}"):
            st.session_state[f"_reset_{tid}"] = True
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
            missing = dependency_report(spec.get("requires", []), mode)
            envk = MODE_REQUIRES.get(mode, (None, None))[1]
            has_key = bool(envk) and os.environ.get(envk, "").startswith(("sk-", "sk-ant-"))
            if missing:
                st.error(
                    "**Cannot Run — packages missing from this app's Python "
                    "environment:**\n\n"
                    + "\n".join(f"- `{PIP_NAME.get(m, m)}` (import `{m}`)" for m in missing)
                    + "\n\nAdd/uncomment them in `requirements.txt` and rebuild (cloud) "
                    "or `pip install -r requirements.txt` (local). Nothing is mocked or "
                    "skipped.")
            elif envk and not has_key:
                st.error(f"**{mode.title()} mode needs `{envk}`.** Set it in "
                         f"*App → Settings → Secrets* (cloud) or your shell (local), "
                         f"or switch to Mock mode in the sidebar.")
            else:
                with st.spinner(f"Running your code ({mode} mode)…"):
                    out, err = run_accumulated(spec, tid, mode)
                st.markdown(f"**Output** · `{mode}` mode")
                st.code(out or "(no stdout)", language="text")
                if err:
                    st.markdown("**Traceback** (real error from your code)")
                    st.code(err, language="text")

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
                st.session_state[f"_loadsol_{tid}"] = True
                st.rerun()
        else:
            st.caption("Try it yourself first — revealing is flagged on the Score page.")


if __name__ == "__main__":
    main()
