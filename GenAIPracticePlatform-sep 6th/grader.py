"""Criterion-based grader.

Grades the LEARNER's submitted code for ONE task against an independent list of
rubric criteria. Each criterion is checked by:
  * AST analysis of the submitted code (was the function actually CALLED? with the
    right argument? does the literal equal 1000, not 500?), and/or
  * runtime inspection of the executed namespace (is `documents` a non-empty list
    of Documents? did similarity_search return 3? is the answer from an LLM call
    or a hardcoded string?).

No broad regex / substring / "keyword appears somewhere" checks.

Public API:

    grade_task(task_id, learner_code, *, lab_id="01-rag",
               accumulated_source=None, mode="mock", dev=False) -> dict

Returns:

    {
      "task_id": 2, "lab_id": "01-rag",
      "score": 12.0, "max_score": 20,
      "runtime": {"executed": True, "error": None},
      "criteria": [
        {"name": "chunk_size_1000", "points": 4, "earned": 0, "passed": False,
         "reason": "splitter called with chunk_size=500, not 1000"},
        ...
      ],
    }

Labs without hand-written criteria fall back to the caller's regex checks.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import os
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

HERE = Path(__file__).resolve().parent

PREAMBLE_IMPORTS = (
    "from sandbox import (get_chat_model, get_embeddings, get_tools, split_docs,\n"
    "                     load_sample_docs, make_vectorstore, supports_tool_calling,\n"
    "                     mcp_stdio_config, resolve_mode,\n"
    "                     SAMPLE_PDF, QUESTION_SET_PDF, MCP_SERVER_PATH)\n"
)


def preamble(mode: str) -> str:
    return (
        "import os as _os, sys as _sys\n"
        f"_sys.path.insert(0, r'{HERE}')\n"
        f"_os.environ['SANDBOX_MODE'] = '{mode}'\n"
        "import sandbox\n"
        + PREAMBLE_IMPORTS
        + f"MODE = '{mode}'\n"
        "# ---------------- learner code below ----------------\n"
    )


def assemble_source(task_codes: list[str], mode: str) -> str:
    """preamble + Task 1..N concatenated, as the Run button builds it."""
    blocks = [f"# ===== Task {i + 1} =====\n{c}" for i, c in enumerate(task_codes)]
    return preamble(mode) + "\n\n".join(blocks)

# --------------------------------------------------------------------------- #
#  AST toolbox                                                                 #
# --------------------------------------------------------------------------- #
def safe_parse(code: str) -> tuple[Optional[ast.AST], Optional[str]]:
    try:
        return ast.parse(code), None
    except SyntaxError as exc:
        return None, f"SyntaxError: {exc.msg} (line {exc.lineno})"


def dotted(node: ast.AST) -> str:
    """'PyPDFLoader', 'loader.load', 'vectorstore.similarity_search', 'ChatPromptTemplate.from_template'."""
    if isinstance(node, ast.Attribute):
        base = dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        return dotted(node.func)
    return ""


def iter_calls(tree: ast.AST):
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            yield n


def calls_named(tree: ast.AST, *names: str, endswith: tuple[str, ...] = ()) -> list[ast.Call]:
    """Every Call whose (dotted) function name equals one of `names`, or (last
    segment) ends with one of `endswith`."""
    out = []
    for c in iter_calls(tree):
        d = dotted(c.func)
        last = d.split(".")[-1]
        if d in names or last in names or (endswith and last.endswith(endswith)):
            out.append(c)
    return out


def imports(tree: ast.AST) -> list[tuple[str, str]]:
    """[(module, name)] for `from module import name` and `import module` (name='')."""
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            for a in n.names:
                out.append((n.module or "", a.asname or a.name))
        elif isinstance(n, ast.Import):
            for a in n.names:
                out.append((a.name, ""))
    return out


def int_env(tree: ast.AST) -> dict[str, int]:
    """Simple `name = <int literal>` assignments in the submitted code."""
    env: dict[str, int] = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            v = n.value
            if isinstance(v, ast.Constant) and isinstance(v.value, int):
                env[n.targets[0].id] = v.value
    return env


def as_int(node: Optional[ast.AST], env: dict[str, int], ns: Optional[dict] = None) -> Optional[int]:
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = as_int(node.operand, env, ns)
        return -v if v is not None else None
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        if ns is not None and isinstance(ns.get(node.id), int):
            return ns[node.id]
    return None


def get_kwarg(call: ast.Call, name: str) -> Optional[ast.AST]:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def get_arg(call: ast.Call, pos: int, name: str) -> Optional[ast.AST]:
    kw = get_kwarg(call, name)
    if kw is not None:
        return kw
    return call.args[pos] if len(call.args) > pos else None


def dict_lookup(node: Optional[ast.AST], key: str) -> Optional[ast.AST]:
    if isinstance(node, ast.Dict):
        for k, v in zip(node.keys, node.values):
            if isinstance(k, ast.Constant) and k.value == key:
                return v
    return None


def is_name(node: Optional[ast.AST], *names: str) -> bool:
    return isinstance(node, ast.Name) and node.id in names


def str_value(node: Optional[ast.AST]) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
        return "".join(parts)
    return None


def assigned_from(tree: ast.AST, var: str) -> list[ast.AST]:
    """RHS value nodes of every `var = <...>` assignment."""
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(is_name(t, var) for t in n.targets):
            out.append(n.value)
        if isinstance(n, ast.AnnAssign) and is_name(n.target, var) and n.value is not None:
            out.append(n.value)
    return out


def call_uses_name(call: ast.Call, name: str) -> bool:
    """Does any positional/keyword arg (recursively) reference Name `name`?"""
    for sub in ast.walk(call):
        if isinstance(sub, ast.Name) and sub.id == name:
            return True
    return False


def func_def(tree: ast.AST, name: str) -> Optional[ast.FunctionDef]:
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    return None


def body_is_stub(fn: ast.FunctionDef) -> bool:
    real = [s for s in fn.body if not (isinstance(s, ast.Expr) and
            isinstance(s.value, ast.Constant) and s.value.value is Ellipsis)]
    real = [s for s in real if not isinstance(s, ast.Pass)]
    real = [s for s in real if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
            and isinstance(s.value.value, str))]  # drop docstring
    return len(real) == 0


def while_true_loops(tree: ast.AST) -> list[ast.While]:
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.While):
            t = n.test
            if (isinstance(t, ast.Constant) and t.value) or is_name(t, "True"):
                out.append(n)
    return out


# --------------------------------------------------------------------------- #
#  runtime helpers                                                             #
# --------------------------------------------------------------------------- #
def is_doc_list(obj: Any, *, min_len: int = 1) -> bool:
    if not isinstance(obj, (list, tuple)) or len(obj) < min_len:
        return False
    return all(hasattr(d, "page_content") for d in obj)


def shares_tokens(a: str, b: str, *, n: int = 3) -> bool:
    """True if `a` reuses a run of >= n words from `b` (grounding heuristic)."""
    wa = [w for w in "".join(c.lower() if c.isalnum() else " " for c in a).split() if len(w) > 2]
    wb = set("".join(c.lower() if c.isalnum() else " " for c in b).split())
    run = 0
    for w in wa:
        run = run + 1 if w in wb else 0
        if run >= n:
            return True
    return False


# --------------------------------------------------------------------------- #
#  context + criterion types                                                   #
# --------------------------------------------------------------------------- #
@dataclass
class Ctx:
    code: str
    tree: Optional[ast.AST]
    syntax_error: Optional[str]
    ns: Optional[dict]
    run_error: Optional[str]
    run_output: str
    mode: str
    ints: dict[str, int] = field(default_factory=dict)


@dataclass
class Criterion:
    name: str
    points: float
    check: Callable[[Ctx], tuple[bool, str]]


# --------------------------------------------------------------------------- #
#  namespace builder (for runtime criteria)                                    #
# --------------------------------------------------------------------------- #
_NS_CACHE: dict[str, tuple[Optional[dict], str, Optional[str]]] = {}


def build_namespace(accumulated_source: str) -> tuple[Optional[dict], str, Optional[str]]:
    key = hashlib.sha1(accumulated_source.encode("utf-8")).hexdigest()
    if key in _NS_CACHE:
        return _NS_CACHE[key]
    demo = iter(["What is the standard notice period?", "How many casual leave days?",
                 "exit", "exit", "exit"])
    ns: dict[str, Any] = {"__name__": "__grader__", "input": lambda *_a: next(demo, "exit")}
    cap = tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace")
    err = None
    try:
        with contextlib.redirect_stdout(cap), contextlib.redirect_stderr(cap):
            exec(compile(accumulated_source, "<grader>", "exec"), ns)  # noqa: S102
    except SystemExit:
        pass
    except BaseException:  # noqa: BLE001
        err = traceback.format_exc()
    cap.seek(0)
    out = cap.read()
    cap.close()
    res = (ns, out, err)
    _NS_CACHE[key] = res
    if len(_NS_CACHE) > 24:
        _NS_CACHE.pop(next(iter(_NS_CACHE)))
    return res


# --------------------------------------------------------------------------- #
#  RAG lab criteria                                                            #
# --------------------------------------------------------------------------- #
_PDF_LOADERS = ("PyPDFLoader", "PyPDFium2Loader", "PyMuPDFLoader", "PDFMinerLoader",
                "PDFPlumberLoader", "UnstructuredPDFLoader", "AmazonTextractPDFLoader")
_NON_PDF_LOADERS = ("TextLoader", "CSVLoader", "JSONLoader", "WebBaseLoader",
                    "UnstructuredFileLoader", "DirectoryLoader", "BSHTMLLoader")


def _t1_loader_imported(c: Ctx):
    for mod, name in imports(c.tree):
        if name in _PDF_LOADERS:
            return True, f"imported `{name}`"
        if name in _NON_PDF_LOADERS:
            return False, f"`{name}` is not a PDF loader"
    return False, "no PDF loader imported (need PyPDFLoader from langchain_community.document_loaders)"


def _t1_loader_called(c: Ctx):
    calls = calls_named(c.tree, *_PDF_LOADERS)
    if not calls:
        if calls_named(c.tree, *_NON_PDF_LOADERS):
            return False, "instantiated a non-PDF loader"
        return False, "PDF loader is never instantiated (imported ≠ used)"
    for call in calls:
        a0 = get_arg(call, 0, "file_path")
        if is_name(a0, "SAMPLE_PDF"):
            return True, "PyPDFLoader(SAMPLE_PDF)"
        s = str_value(a0)
        if s and s.lower().endswith(".pdf"):
            return True, f"PyPDFLoader({s!r})"
    return False, "loader called, but not with SAMPLE_PDF / a .pdf path"


def _t1_documents_loaded(c: Ctx):
    ok_ast = False
    for val in assigned_from(c.tree, "documents"):
        if isinstance(val, ast.Call) and dotted(val.func).split(".")[-1] == "load":
            ok_ast = True
        if isinstance(val, ast.List) and not val.elts:
            return False, "`documents = []` — empty, not loaded"
        if isinstance(val, ast.Constant) and val.value is None:
            return False, "`documents = None`"
    if not ok_ast:
        return False, "`documents` is not assigned from a `.load()` call"
    if c.ns is not None:
        d = c.ns.get("documents")
        if not is_doc_list(d):
            return False, f"at runtime `documents` is {type(d).__name__} / empty, not loaded Documents"
        return True, f".load() → {len(d)} Documents"
    return True, "documents assigned from .load() (runtime not checked)"


def _splitter_call(tree):
    calls = calls_named(tree, endswith=("TextSplitter",))
    return calls[0] if calls else None


def _t2_splitter_created(c: Ctx):
    call = _splitter_call(c.tree)
    if call is None:
        if any(n == "RecursiveCharacterTextSplitter" for _, n in imports(c.tree)):
            return False, "splitter imported but never instantiated"
        return False, "no text splitter instantiated"
    name = dotted(call.func).split(".")[-1]
    if name != "RecursiveCharacterTextSplitter":
        return True, f"used `{name}` (task asks for RecursiveCharacterTextSplitter)"
    return True, "RecursiveCharacterTextSplitter(...) created"


def _t2_param(c: Ctx, kw: str, want: int, pos: int):
    call = _splitter_call(c.tree)
    if call is None:
        return False, "no splitter to configure"
    node = get_arg(call, pos, kw)
    if node is None:
        return False, f"`{kw}` not passed to the splitter"
    val = as_int(node, c.ints, c.ns)
    if val is None:
        return False, f"`{kw}` value could not be resolved to an int"
    if val != want:
        return False, f"splitter called with {kw}={val}, not {want}"
    return True, f"{kw}={want}"


def _t2_documents_split(c: Ctx):
    ok_ast = None
    for call in calls_named(c.tree, "split_documents"):
        a0 = get_arg(call, 0, "documents")
        if is_name(a0, "documents"):
            ok_ast = call
            break
        ok_ast = ok_ast or call
    if ok_ast is None:
        return False, "`split_documents(...)` is never called"
    if not any(is_name(get_arg(ok_ast, 0, "documents"), "documents") for _ in [0]):
        return False, "`split_documents` called, but not on `documents`"
    stored = any(isinstance(v, ast.Call) and dotted(v.func).split(".")[-1] == "split_documents"
                 for v in assigned_from(c.tree, "chunks"))
    if c.ns is not None:
        ch = c.ns.get("chunks")
        if not is_doc_list(ch):
            return False, f"at runtime `chunks` is {type(ch).__name__} / empty"
        docs = c.ns.get("documents")
        if is_doc_list(docs) and len(ch) < len(docs):
            return False, f"only {len(ch)} chunks from {len(docs)} pages — not really split"
        return True, f"documents → {len(ch)} chunks" + ("" if stored else " (not stored in `chunks`)")
    return (True, "split_documents(documents) called") if stored else \
           (True, "split_documents(documents) called (result not stored in `chunks`)")


def _t2_count_reported(c: Ctx):
    for call in calls_named(c.tree, "print"):
        for a in ast.walk(call):
            if isinstance(a, ast.Call) and dotted(a.func) == "len":
                inner = a.args[0] if a.args else None
                if is_name(inner, "chunks"):
                    return True, "print(... len(chunks) ...)"
                if is_name(inner, "documents"):
                    return False, "prints len(documents), not len(chunks)"
        s = str_value(call.args[0]) if call.args else None
        if s and "len(chunks)" in s.replace(" ", ""):
            return True, "prints len(chunks)"
    return False, "the chunk count (len(chunks)) is never printed"


def _emb_call(tree):
    return (calls_named(tree, "get_embeddings", "OpenAIEmbeddings", "FastEmbedEmbeddings",
                        "HuggingFaceEmbeddings", endswith=("Embeddings",)))


def _t3_embeddings_created(c: Ctx):
    calls = _emb_call(c.tree)
    if not calls:
        return False, "no embeddings object created"
    for v in assigned_from(c.tree, "embeddings"):
        if isinstance(v, ast.Constant) and v.value is None:
            return False, "`embeddings = None`"
    if c.ns is not None and c.ns.get("embeddings") is None:
        return False, "at runtime `embeddings` is None"
    return True, f"{dotted(calls[0].func).split('.')[-1]}(...) created"


def _t3_model_correct(c: Ctx):
    for call in calls_named(c.tree, "get_embeddings"):
        if is_name(get_arg(call, 0, "mode"), "MODE"):
            return True, "get_embeddings(MODE) — model selected by the sandbox"
    for call in calls_named(c.tree, "OpenAIEmbeddings"):
        m = str_value(get_arg(call, 0, "model"))
        if m == "text-embedding-3-small":
            return True, "OpenAIEmbeddings(model='text-embedding-3-small')"
        if m:
            return False, f"model is '{m}', not 'text-embedding-3-small'"
        return False, "OpenAIEmbeddings without model='text-embedding-3-small'"
    if _emb_call(c.tree):
        return True, "embeddings model provided by the helper/class"
    return False, "no embeddings model specified"


def _vs_call(tree):
    out = calls_named(tree, "make_vectorstore")
    for call in iter_calls(tree):
        d = dotted(call.func)
        if d in ("Chroma.from_documents", "Chroma") or d.endswith(".from_documents"):
            out.append(call)
    return out


def _t3_vectorstore_created(c: Ctx):
    calls = _vs_call(c.tree)
    if not calls:
        return False, "no vector store created (make_vectorstore / Chroma.from_documents)"
    for v in assigned_from(c.tree, "vectorstore"):
        if isinstance(v, ast.Constant) and v.value is None:
            return False, "`vectorstore = None`"
    if c.ns is not None:
        vs = c.ns.get("vectorstore")
        if vs is None or not hasattr(vs, "similarity_search"):
            return False, "at runtime `vectorstore` has no .similarity_search"
        return True, f"{type(vs).__name__} ready"
    return True, f"{dotted(calls[0].func).split('.')[-1]}(...) created"


def _t3_chunks_indexed(c: Ctx):
    for call in _vs_call(c.tree):
        arg = get_arg(call, 0, "documents") or get_kwarg(call, "documents")
        if is_name(arg, "chunks"):
            return True, "chunks passed to the vector store"
        if is_name(arg, "documents"):
            return False, "indexed `documents` (pages), not `chunks`"
        if isinstance(arg, ast.List) and not arg.elts:
            return False, "indexed an empty list"
    return False, "`chunks` are not passed to the vector store"


def _sim_search_calls(tree):
    return [c for c in iter_calls(tree)
            if dotted(c.func).split(".")[-1] == "similarity_search"]


def _t3_search_k3(c: Ctx):
    calls = _sim_search_calls(c.tree)
    if not calls:
        return False, "`.similarity_search(...)` is never called"
    for call in calls:
        k = get_arg(call, 1, "k")
        kv = as_int(k, c.ints, c.ns)
        if kv == 3:
            return True, "similarity_search(query, k=3)"
        if kv is not None:
            return False, f"similarity_search called with k={kv}, not 3"
    return False, "similarity_search called without k=3 (default k is 4)"


def _t3_results_obtained(c: Ctx):
    if c.ns is None:
        return False, "runtime not available"
    for name in ("results", "docs", "hits", "matches"):
        r = c.ns.get(name)
        if is_doc_list(r):
            extra = "" if len(r) == 3 else f" (got {len(r)}, expected 3)"
            return (len(r) == 3), f"retrieved {len(r)} documents{extra}"
    return False, "no list of retrieved Documents found at runtime"


def _retriever_calls(tree):
    return [c for c in iter_calls(tree) if dotted(c.func).split(".")[-1] == "as_retriever"]


def _t4_retriever_created(c: Ctx):
    calls = _retriever_calls(c.tree)
    if calls:
        for v in assigned_from(c.tree, "retriever"):
            if isinstance(v, ast.Constant) and v.value is None:
                return False, "`retriever = None`"
        return True, "vectorstore.as_retriever(...)"
    if _sim_search_calls(c.tree):
        return True, "retrieval via vectorstore.similarity_search(...)"
    return False, "no retriever created and no similarity_search used"


def _t4_retrieval_k3(c: Ctx):
    for call in _retriever_calls(c.tree):
        sk = get_kwarg(call, "search_kwargs")
        kv = as_int(dict_lookup(sk, "k"), c.ints, c.ns)
        if kv == 3:
            return True, "as_retriever(search_kwargs={'k': 3})"
        if kv is not None:
            return False, f"retriever k={kv}, not 3"
    for call in _sim_search_calls(c.tree):
        if as_int(get_arg(call, 1, "k"), c.ints, c.ns) == 3:
            return True, "similarity_search(..., k=3)"
    return False, "retrieval k is not set to 3"


def _t4_llm_created(c: Ctx):
    calls = calls_named(c.tree, "get_chat_model", "ChatOpenAI", "ChatAnthropic")
    if not calls:
        return False, "no chat model created"
    for v in assigned_from(c.tree, "llm"):
        if isinstance(v, ast.Constant) and v.value is None:
            return False, "`llm = None`"
    for call in calls_named(c.tree, "get_chat_model"):
        if is_name(get_arg(call, 0, "mode"), "MODE"):
            return True, "get_chat_model(MODE)"
    return True, f"{dotted(calls[0].func).split('.')[-1]}(...)"


def _all_template_strings(tree):
    out = []
    for call in iter_calls(tree):
        if dotted(call.func).split(".")[-1] in ("from_template", "from_messages"):
            for a in list(call.args) + [k.value for k in call.keywords]:
                s = str_value(a)
                if s:
                    out.append(s)
    for v in assigned_from(tree, "prompt"):
        s = str_value(v)
        if s:
            out.append(s)
    return out


def _t4_prompt_grounded(c: Ctx):
    strings = _all_template_strings(c.tree)
    if not strings:
        return False, "no ChatPromptTemplate.from_template(...) string found"
    joined = "\n".join(strings)
    has_ctx = "{context}" in joined
    has_q = "{question}" in joined
    has_refusal = "could not find the answer in the provided document" in joined.lower()
    if has_ctx and has_q and has_refusal:
        return True, "prompt has {context}, {question} and the exact refusal line"
    missing = [x for x, ok in (("{context}", has_ctx), ("{question}", has_q),
                               ("refusal sentence", has_refusal)) if not ok]
    return False, "prompt is missing: " + ", ".join(missing)


def _t4_retrieval_executed(c: Ctx):
    ok = any(dotted(call.func).split(".")[-1] in ("invoke", "get_relevant_documents")
             and is_name(call.func.value if isinstance(call.func, ast.Attribute) else None, "retriever")
             for call in iter_calls(c.tree))
    ok = ok or bool(_sim_search_calls(c.tree))
    if not ok:
        return False, "retriever.invoke(...) / similarity_search(...) is never called"
    if c.ns is not None:
        for name in ("docs", "retrieved_docs", "results", "context_docs"):
            if is_doc_list(c.ns.get(name)):
                return True, f"retrieved {len(c.ns[name])} documents"
    return True, "retrieval call present"


def _context_var_from_docs(tree) -> Optional[str]:
    """Name of a variable built by joining page_content of retrieved docs."""
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            src = ast.dump(n.value)
            if "page_content" in src or ("join" in src and ("docs" in src or "d " in src)):
                return n.targets[0].id
    return None


def _t4_context_built(c: Ctx):
    var = _context_var_from_docs(c.tree)
    if var:
        return True, f"`{var}` built from retrieved docs' page_content"
    for v in assigned_from(c.tree, "context"):
        if str_value(v) is not None:
            return False, "`context` is a hardcoded string, not from retrieved docs"
    return False, "no context assembled from the retrieved documents"


def _t4_context_to_llm(c: Ctx):
    var = _context_var_from_docs(c.tree) or "context"
    for call in iter_calls(c.tree):
        last = dotted(call.func).split(".")[-1]
        if last == "invoke" and isinstance(call.func, ast.Attribute) and \
                is_name(call.func.value, "llm", "chain"):
            if call_uses_name(call, var) or any(
                    call_uses_name(call, var) for call in iter_calls(call)):
                return True, f"llm.invoke(...) receives `{var}`"
            # invoke(prompt.format_messages(context=..., question=...))
            for sub in ast.walk(call):
                if isinstance(sub, ast.Call) and dotted(sub.func).split(".")[-1] == "format_messages":
                    if get_kwarg(sub, "context") is not None or call_uses_name(sub, var):
                        return True, "prompt.format_messages(context=...) fed to llm.invoke"
            return False, "llm.invoke(...) is called, but without the retrieved context"
    if calls_named(c.tree, endswith=("invoke",)):
        return False, "an .invoke(...) exists but not on `llm`/`chain` with context"
    return False, "the LLM is never invoked with the context"


def _t4_answer_from_llm(c: Ctx):
    hard = False
    for v in list(assigned_from(c.tree, "resp")) + list(assigned_from(c.tree, "answer")) + \
            list(assigned_from(c.tree, "response")):
        if str_value(v) is not None:
            hard = True
        if isinstance(v, ast.Call) and dotted(v.func).split(".")[-1] == "invoke":
            if c.ns is not None:
                r = c.ns.get("resp") or c.ns.get("response")
                if r is not None and hasattr(r, "content"):
                    grounded = True
                    ctxs = c.ns.get("context")
                    if isinstance(ctxs, str) and r.content:
                        grounded = shares_tokens(str(r.content), ctxs) or \
                                   "could not find the answer" in str(r.content).lower()
                    return (grounded,
                            "answer generated by llm.invoke" +
                            ("" if grounded else " but not grounded in the retrieved context"))
            return True, "answer produced by an .invoke(...) call"
    if hard:
        return False, "answer is a hardcoded string, not generated by the LLM"
    return False, "no LLM-generated answer (`resp = llm.invoke(...)`)"


def _fn_calls(fn: ast.FunctionDef, last_name: str) -> bool:
    return any(dotted(c.func).split(".")[-1] == last_name for c in iter_calls(fn))


def _t5_answer_fn(c: Ctx):
    fn = func_def(c.tree, "answer")
    if fn is None:
        return False, "no `def answer(question):`"
    if body_is_stub(fn):
        return False, "`answer()` body is a stub (`...` / `pass`)"
    if not any(isinstance(n, ast.Return) and n.value is not None for n in ast.walk(fn)):
        return False, "`answer()` never returns a value"
    return True, "answer(question) defined with a real body + return"


def _t5_fn_retrieves(c: Ctx):
    fn = func_def(c.tree, "answer")
    if fn is None:
        return False, "no answer() function"
    if _fn_calls(fn, "invoke") and any(
            is_name(cc.func.value, "retriever") for cc in iter_calls(fn)
            if isinstance(cc.func, ast.Attribute)):
        return True, "answer() calls retriever.invoke(...)"
    if _fn_calls(fn, "similarity_search"):
        return True, "answer() calls similarity_search(...)"
    return False, "answer() does not retrieve documents"


def _t5_fn_llm_context(c: Ctx):
    fn = func_def(c.tree, "answer")
    if fn is None:
        return False, "no answer() function"
    has_llm = any(dotted(cc.func).split(".")[-1] == "invoke" and isinstance(cc.func, ast.Attribute)
                  and is_name(cc.func.value, "llm", "chain") for cc in iter_calls(fn))
    has_ctx = _context_var_from_docs(fn) is not None or any(
        isinstance(n, ast.Attribute) and n.attr == "page_content" for n in ast.walk(fn))
    if has_llm and has_ctx:
        return True, "answer() builds context from docs and invokes the LLM"
    miss = []
    if not has_llm:
        miss.append("llm.invoke")
    if not has_ctx:
        miss.append("context from page_content")
    return False, "answer() missing: " + ", ".join(miss)


def _t5_loop(c: Ctx):
    loops = while_true_loops(c.tree)
    if not loops:
        return False, "no `while True:` interactive loop"
    if any(any(dotted(cc.func) == "input" for cc in iter_calls(lp)) for lp in loops):
        return True, "while True: with input(...)"
    return False, "loop present but never calls input()"


def _t5_reads_input(c: Ctx):
    if any(dotted(cc.func) == "input" for lp in while_true_loops(c.tree) for cc in iter_calls(lp)):
        return True, "input() read inside the loop"
    if any(dotted(cc.func) == "input" for cc in iter_calls(c.tree)):
        return True, "input() is used"
    return False, "input() is never called"


def _t5_exit(c: Ctx):
    for lp in while_true_loops(c.tree):
        has_break = any(isinstance(n, ast.Break) for n in ast.walk(lp))
        mentions_exit = any(
            (str_value(cmp) or "").lower() in ("exit", "quit")
            for n in ast.walk(lp) if isinstance(n, ast.Compare)
            for cmp in [n.left, *n.comparators])
        mentions_exit = mentions_exit or any(
            (str_value(e) or "").lower() in ("exit", "quit")
            for n in ast.walk(lp) if isinstance(n, ast.Constant) for e in [n])
        if has_break and mentions_exit:
            return True, "breaks the loop on 'exit'"
        if has_break and not mentions_exit:
            return False, "loop breaks, but not specifically on 'exit'"
    return False, "loop never stops on 'exit' (no break on 'exit')"


def _t5_calls_answer(c: Ctx):
    for lp in while_true_loops(c.tree):
        if any(dotted(cc.func) == "answer" for cc in iter_calls(lp)):
            return True, "the loop calls answer(...)"
    return False, "the loop never calls answer(...)"


RAG_CRITERIA: dict[int, list[Criterion]] = {
    1: [
        Criterion("loader_imported", 1, _t1_loader_imported),
        Criterion("loader_called_with_pdf_path", 2, _t1_loader_called),
        Criterion("documents_actually_loaded", 2, _t1_documents_loaded),
    ],
    2: [
        Criterion("splitter_created", 3, _t2_splitter_created),
        Criterion("chunk_size_1000", 4, lambda c: _t2_param(c, "chunk_size", 1000, 0)),
        Criterion("chunk_overlap_200", 4, lambda c: _t2_param(c, "chunk_overlap", 200, 1)),
        Criterion("documents_split", 5, _t2_documents_split),
        Criterion("chunk_count_reported", 4, _t2_count_reported),
    ],
    3: [
        Criterion("embeddings_created", 5, _t3_embeddings_created),
        Criterion("embedding_model_correct", 4, _t3_model_correct),
        Criterion("vectorstore_created", 6, _t3_vectorstore_created),
        Criterion("chunks_indexed", 4, _t3_chunks_indexed),
        Criterion("similarity_search_k3", 4, _t3_search_k3),
        Criterion("top3_results_obtained", 2, _t3_results_obtained),
    ],
    4: [
        Criterion("retriever_created", 4, _t4_retriever_created),
        Criterion("retrieval_k_is_3", 3, _t4_retrieval_k3),
        Criterion("llm_created", 3, _t4_llm_created),
        Criterion("prompt_is_grounded", 3, _t4_prompt_grounded),
        Criterion("retrieval_executed", 3, _t4_retrieval_executed),
        Criterion("context_built_from_docs", 3, _t4_context_built),
        Criterion("context_passed_to_llm", 3, _t4_context_to_llm),
        Criterion("answer_generated_by_llm", 3, _t4_answer_from_llm),
    ],
    5: [
        Criterion("answer_function_defined", 4, _t5_answer_fn),
        Criterion("answer_retrieves", 4, _t5_fn_retrieves),
        Criterion("answer_invokes_llm_with_context", 5, _t5_fn_llm_context),
        Criterion("interactive_while_loop", 4, _t5_loop),
        Criterion("reads_user_input", 2, _t5_reads_input),
        Criterion("stops_on_exit", 3, _t5_exit),
        Criterion("loop_calls_answer", 3, _t5_calls_answer),
    ],
}

LAB_CRITERIA: dict[str, dict[int, list[Criterion]]] = {"01-rag": RAG_CRITERIA}


# --------------------------------------------------------------------------- #
#  public entry point                                                         #
# --------------------------------------------------------------------------- #
def has_criteria(lab_id: str, task_id: int) -> bool:
    return task_id in LAB_CRITERIA.get(lab_id, {})


def grade_task(task_id: int, learner_code: str, *, lab_id: str = "01-rag",
               accumulated_source: Optional[str] = None, mode: str = "mock",
               dev: bool = False) -> dict:
    crits = LAB_CRITERIA.get(lab_id, {}).get(task_id)
    if not crits:
        raise KeyError(f"no criteria for {lab_id} task {task_id}")

    tree, syn = safe_parse(learner_code)
    ns = out = run_err = None
    # runtime criteria need the executed namespace; cheap after the first call (cached)
    if accumulated_source is not None and tree is not None:
        ns, out, run_err = build_namespace(accumulated_source)

    ctx = Ctx(code=learner_code, tree=tree, syntax_error=syn, ns=ns,
              run_error=run_err, run_output=out or "", mode=mode,
              ints=int_env(tree) if tree else {})

    rows, earned_total = [], 0.0
    for crit in crits:
        if tree is None:
            passed, reason = False, f"cannot grade — {syn}"
        else:
            try:
                passed, reason = crit.check(ctx)
            except Exception as exc:  # noqa: BLE001 — a criterion bug must not crash grading
                passed, reason = False, f"[criterion error: {exc.__class__.__name__}: {exc}]"
        got = crit.points if passed else 0.0
        earned_total += got
        rows.append({"name": crit.name, "points": crit.points, "earned": round(got, 2),
                     "passed": bool(passed), "reason": reason})

    max_score = sum(c.points for c in crits)
    result = {
        "task_id": task_id, "lab_id": lab_id,
        "score": round(earned_total, 1), "max_score": max_score,
        "runtime": {"executed": ns is not None and run_err is None,
                    "error": (run_err.strip().splitlines()[-1] if run_err else None)},
        "criteria": rows,
    }
    if dev:
        result["_source"] = accumulated_source
        result["_run_output"] = out
    return result
