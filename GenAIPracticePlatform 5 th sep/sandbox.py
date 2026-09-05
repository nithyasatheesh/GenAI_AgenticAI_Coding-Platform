"""Sandbox runtime — helpers injected into every learner "Run".

Design: **REAL execution is the primary path. Mock is a demo fallback.**

Modes (resolved by `resolve_mode`):
    "openai"  -> langchain_openai.ChatOpenAI + OpenAIEmbeddings   (needs OPENAI_API_KEY)
    "claude"  -> langchain_anthropic.ChatAnthropic + FastEmbed local embeddings
                 (needs ANTHROPIC_API_KEY; Anthropic has no embeddings API)
    "mock"    -> a local BaseChatModel that answers from retrieved context + local
                 embeddings. NO network, NO key. Demonstration only — a real
                 tool-calling / agent LLM is required for the agent labs.
    "auto"    -> openai if OPENAI_API_KEY else claude if ANTHROPIC_API_KEY else mock

Real, not simulated, in every mode:
  * Python execution (the app `exec()`s your code in this interpreter)
  * document loading, text splitting, prompts, chains, LangGraph graphs
  * the vector store — real **ChromaDB** (falls back to LangChain's
    InMemoryVectorStore only if chromadb can't be imported)
  * embeddings — real: `OpenAIEmbeddings` (openai mode) or local **FastEmbed**
    ONNX model (mock/claude). `DeterministicFakeEmbedding` is a last-resort
    fallback and prints a warning when used.

The API key is read from an environment variable / server-side secret only. It is
never hard-coded and never sent to the browser.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "content" / "_data"
SAMPLE_PDF = str(DATA_DIR / "sample_knowledge_base.pdf")
QUESTION_SET_PDF = str(DATA_DIR / "RAG_Question_Set.pdf")
MCP_SERVER_PATH = str(HERE / "mcp_server.py")

MODE = os.environ.get("SANDBOX_MODE", "auto").lower()  # overwritten per-run by the app

DEFAULT_OPENAI_CHAT = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_OPENAI_EMBED = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
DEFAULT_ANTHROPIC_CHAT = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
DEFAULT_FASTEMBED = os.environ.get("FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5")


# --------------------------------------------------------------------------- #
#  mode / key resolution                                                       #
# --------------------------------------------------------------------------- #
def has_openai() -> bool:
    return os.environ.get("OPENAI_API_KEY", "").startswith("sk-")


def has_anthropic() -> bool:
    return os.environ.get("ANTHROPIC_API_KEY", "").startswith("sk-ant-")


def resolve_mode(requested: Optional[str] = None) -> str:
    m = (requested or MODE or "auto").lower()
    if m in ("real", "auto"):
        return "openai" if has_openai() else "claude" if has_anthropic() else "mock"
    return "claude" if m == "anthropic" else m


# --------------------------------------------------------------------------- #
#  mock chat model — a real langchain_core BaseChatModel (context-grounded)     #
# --------------------------------------------------------------------------- #
def _mock_chat_class():
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult

    _STOP = set("a an the of to and or is are was were be in on at for with as by "
                "it its this that from what how many do does you your".split())

    def _toks(s: str):
        return [w for w in "".join(c.lower() if c.isalnum() else " " for c in s).split()
                if w not in _STOP and len(w) > 1]

    class MockGroundedChat(BaseChatModel):
        """Demo only. Answers from a 'Context:' block; cannot do tool calling."""

        model: str = "mock-grounded-1"
        temperature: float = 0.0

        @property
        def _llm_type(self) -> str:
            return "mock-grounded"

        def _generate(self, messages, stop=None, run_manager=None, **kw) -> ChatResult:
            prompt = messages[-1].content if messages else ""
            ctx, question = prompt, ""
            if "Context:" in prompt and "Question:" in prompt:
                ctx = prompt.split("Context:", 1)[1].split("Question:", 1)[0]
                question = prompt.split("Question:", 1)[1]
            q = set(_toks(question)) or set(_toks(prompt))
            best, score = "", 0
            for sent in ctx.replace("\n", " ").split("."):
                overlap = len(q & set(_toks(sent)))
                if overlap > score:
                    best, score = sent.strip(), overlap
            text = (best + ".") if (score and best) else \
                "I could not find the answer in the provided document."
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    return MockGroundedChat


# --------------------------------------------------------------------------- #
#  factories                                                                   #
# --------------------------------------------------------------------------- #
def get_chat_model(mode: Optional[str] = None, *, model: Optional[str] = None,
                   temperature: float = 0.0, **kw: Any):
    mode = resolve_mode(mode)
    if mode == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model or DEFAULT_OPENAI_CHAT, temperature=temperature, **kw)
    if mode == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model or DEFAULT_ANTHROPIC_CHAT,
                             temperature=temperature, **kw)
    return _mock_chat_class()(model="mock-grounded-1", temperature=temperature)


def supports_tool_calling(mode: Optional[str] = None) -> bool:
    """Mock cannot emit tool calls — agent labs need a real LLM."""
    return resolve_mode(mode) in ("openai", "claude")


def check_llm(mode: Optional[str] = None) -> tuple[bool, str]:
    """Make ONE tiny real call to confirm the key + model actually work.
    Returns (ok, detail). Used by the app to show a key-status line so an
    invalid key is caught immediately, not five Runs later."""
    mode = resolve_mode(mode)
    if mode == "mock":
        return True, "Mock mode — no key required."
    try:
        model = get_chat_model(mode, max_tokens=5)
        model.invoke("ping")
        return True, f"{mode} key valid — model `{getattr(model, 'model', mode)}` responded."
    except Exception as exc:  # noqa: BLE001
        return False, f"{exc.__class__.__name__}: {str(exc)[:280]}"


def _local_embeddings(model: Optional[str] = None):
    """Keyless embeddings: real FastEmbed if installed, else a deterministic
    fallback (weak retrieval, but never fails)."""
    try:
        from langchain_community.embeddings import FastEmbedEmbeddings
        return FastEmbedEmbeddings(model_name=model or DEFAULT_FASTEMBED)
    except Exception as exc:  # noqa: BLE001
        print(f"[sandbox] FastEmbed unavailable ({exc.__class__.__name__}: {exc}); "
              f"using DeterministicFakeEmbedding — retrieval quality will be poor. "
              f"(install `requirements-full.txt`, or use OpenAI mode with a valid key)")
        from langchain_core.embeddings import DeterministicFakeEmbedding
        return DeterministicFakeEmbedding(size=384)


def get_embeddings(mode: Optional[str] = None, *, model: Optional[str] = None, **kw: Any):
    mode = resolve_mode(mode)
    if mode == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=model or DEFAULT_OPENAI_EMBED, **kw)
    return _local_embeddings(model)


def split_docs(docs, *, chunk_size: int = 800, chunk_overlap: int = 120):
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap).split_documents(docs)


def _build_store(chunks, embeddings, collection):
    try:
        import chromadb
        from langchain_chroma import Chroma
        return Chroma.from_documents(
            documents=chunks, embedding=embeddings, collection_name=collection,
            client=chromadb.EphemeralClient(),
        )
    except Exception as exc:  # noqa: BLE001 — chromadb not installed
        print(f"[sandbox] ChromaDB unavailable ({exc.__class__.__name__}: {exc}); "
              f"using langchain-core InMemoryVectorStore (same interface).")
        from langchain_core.vectorstores import InMemoryVectorStore
        return InMemoryVectorStore.from_documents(documents=chunks, embedding=embeddings)


def make_vectorstore(chunks, embeddings, *, collection: str = "sandbox_kb"):
    """Build a real vector store. If the embeddings themselves fail (e.g. an
    invalid OPENAI_API_KEY -> 401), retry ONCE with keyless local embeddings so
    the RAG lab still produces a result — with a loud warning."""
    try:
        return _build_store(chunks, embeddings, collection)
    except Exception as exc:  # noqa: BLE001
        print(f"[sandbox] embeddings failed while indexing "
              f"({exc.__class__.__name__}: {str(exc)[:200]}). "
              f"Falling back to LOCAL embeddings — the vectors are NOT from OpenAI. "
              f"Fix OPENAI_API_KEY for real OpenAI embeddings.")
        return _build_store(chunks, _local_embeddings(), collection)


def load_sample_docs():
    from langchain_community.document_loaders import PyPDFLoader
    if os.path.isfile(SAMPLE_PDF):
        return PyPDFLoader(SAMPLE_PDF).load()
    from langchain_core.documents import Document
    return [Document(page_content=_FALLBACK_TEXT,
                     metadata={"source": "fallback", "page": 0})]


# --------------------------------------------------------------------------- #
#  real tools (for the tool-calling / agent / multi-agent labs)               #
# --------------------------------------------------------------------------- #
def get_tools(names: Optional[list[str]] = None):
    """Return real LangChain `@tool` objects. Pass `names` to filter."""
    from langchain_core.tools import tool

    @tool
    def calculator(expression: str) -> str:
        """Evaluate a basic arithmetic expression, e.g. '(2 + 3) * 4 ** 2'."""
        import ast
        import operator as _op
        _ops = {ast.Add: _op.add, ast.Sub: _op.sub, ast.Mult: _op.mul,
                ast.Div: _op.truediv, ast.Pow: _op.pow, ast.Mod: _op.mod,
                ast.USub: _op.neg, ast.UAdd: _op.pos, ast.FloorDiv: _op.floordiv}

        def _ev(n):
            if isinstance(n, ast.Constant):
                return n.value
            if isinstance(n, ast.BinOp):
                return _ops[type(n.op)](_ev(n.left), _ev(n.right))
            if isinstance(n, ast.UnaryOp):
                return _ops[type(n.op)](_ev(n.operand))
            raise ValueError("unsupported expression")

        return str(_ev(ast.parse(expression, mode="eval").body))

    @tool
    def word_count(text: str) -> int:
        """Count the number of whitespace-separated words in `text`."""
        return len(text.split())

    @tool
    def kb_lookup(query: str) -> str:
        """Search the company HR & benefits handbook and return the best passages."""
        vs = make_vectorstore(split_docs(load_sample_docs()), get_embeddings())
        hits = vs.similarity_search(query, k=2)
        return "\n---\n".join(d.page_content[:400] for d in hits) or "no match found"

    all_tools = {t.name: t for t in (calculator, word_count, kb_lookup)}
    return list(all_tools.values()) if not names else [all_tools[n] for n in names]


# --------------------------------------------------------------------------- #
#  MCP                                                                         #
# --------------------------------------------------------------------------- #
def mcp_stdio_config(server_name: str = "sandbox") -> dict:
    """Config for langchain_mcp_adapters.MultiServerMCPClient — launches the
    bundled stdio MCP server (mcp_server.py) as a real subprocess."""
    return {server_name: {"command": sys.executable,
                          "args": [MCP_SERVER_PATH], "transport": "stdio"}}


_FALLBACK_TEXT = (
    "Employees are eligible for 12 days of casual leave in a calendar year. "
    "Employees receive 10 days of sick leave per calendar year. "
    "Employees receive 18 days of earned leave per calendar year. "
    "The standard notice period for regular full-time employees is 60 calendar days. "
    "Economy-class air travel is the standard for domestic business trips. "
    "The standard employee medical insurance coverage limit is INR 5,00,000 per policy year."
)
