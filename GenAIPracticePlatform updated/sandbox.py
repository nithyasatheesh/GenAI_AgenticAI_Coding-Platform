"""Sandbox runtime helpers - injected into every learner "Run".

Two modes, chosen in the sidebar:

    MODE == "mock"  -> no network, no API key. Uses real LangChain classes:
                       a small custom BaseChatModel that answers from the
                       retrieved context, plus DeterministicFakeEmbedding.
    MODE == "real"  -> langchain_openai.ChatOpenAI / OpenAIEmbeddings.
                       Requires OPENAI_API_KEY in the environment / .env.

Everything below runs for real - the pipeline (loaders, splitters, vector store,
retriever, prompt, chains, graphs) is genuine LangChain in both modes. Only the
model + embeddings implementations swap.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "content" / "pdf-rag-knowledge-base" / "data"
SAMPLE_PDF = str(DATA_DIR / "sample_knowledge_base.pdf")

MODE = os.environ.get("SANDBOX_MODE", "mock").lower()  # overwritten per-run by the app


# --------------------------------------------------------------------------- #
#  Mock chat model - a real langchain_core BaseChatModel                       #
# --------------------------------------------------------------------------- #
def _mock_chat_class():
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult

    _STOP = set("a an the of to and or is are was were be in on at for with as by "
                "it its this that from what how many do does you your".split())

    def _tokens(s: str):
        return [w for w in "".join(c.lower() if c.isalnum() else " " for c in s).split()
                if w not in _STOP and len(w) > 1]

    class MockGroundedChat(BaseChatModel):
        """Answers ONLY from a 'Context:' block in the prompt. No network."""

        model: str = "mock-grounded-1"
        temperature: float = 0.0

        @property
        def _llm_type(self) -> str:
            return "mock-grounded"

        def _generate(self, messages, stop=None, run_manager=None, **kw) -> ChatResult:
            prompt = messages[-1].content if messages else ""
            context, question = prompt, ""
            if "Context:" in prompt and "Question:" in prompt:
                context = prompt.split("Context:", 1)[1].split("Question:", 1)[0]
                question = prompt.split("Question:", 1)[1]
            q = set(_tokens(question)) or set(_tokens(prompt))
            best, score = "", 0
            for sent in context.replace("\n", " ").split("."):
                overlap = len(q & set(_tokens(sent)))
                if overlap > score:
                    best, score = sent.strip(), overlap
            if score == 0 or not best:
                text = "I could not find the answer in the provided document."
            else:
                text = best + "."
            msg = AIMessage(content=text)
            return ChatResult(generations=[ChatGeneration(message=msg)])

    return MockGroundedChat


# --------------------------------------------------------------------------- #
#  Public factory helpers                                                      #
# --------------------------------------------------------------------------- #
def get_chat_model(mode: Optional[str] = None, *, model: str = "gpt-4o-mini",
                   temperature: float = 0.0, **kw: Any):
    mode = (mode or MODE).lower()
    if mode == "real":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=temperature, **kw)
    return _mock_chat_class()(model="mock-grounded-1", temperature=temperature)


def get_embeddings(mode: Optional[str] = None, *,
                   model: str = "text-embedding-3-small", **kw: Any):
    mode = (mode or MODE).lower()
    if mode == "real":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=model, **kw)
    from langchain_core.embeddings import DeterministicFakeEmbedding
    return DeterministicFakeEmbedding(size=256)


def load_sample_docs():
    """Load the bundled synthetic knowledge base as LangChain Documents."""
    from langchain_community.document_loaders import PyPDFLoader
    if os.path.isfile(SAMPLE_PDF):
        return PyPDFLoader(SAMPLE_PDF).load()
    from langchain_core.documents import Document
    return [Document(page_content=_FALLBACK_TEXT, metadata={"source": "sample", "page": 0})]


def make_vectorstore(chunks, embeddings):
    """In-memory Chroma (no persistence) - identical API to the VM lab's store."""
    from langchain_chroma import Chroma
    return Chroma.from_documents(documents=chunks, embedding=embeddings,
                                 collection_name="sandbox_kb")


def api_key_present() -> bool:
    return os.environ.get("OPENAI_API_KEY", "").startswith("sk-")


_FALLBACK_TEXT = (
    "Employees are eligible for 12 days of casual leave in a calendar year. "
    "Employees receive 10 days of sick leave per calendar year. "
    "Employees receive 18 days of earned leave per calendar year. "
    "The standard notice period for regular full-time employees is 60 calendar days. "
    "Economy-class air travel is the standard for domestic business trips. "
    "The standard employee medical insurance coverage limit is INR 5,00,000 per policy year."
)
