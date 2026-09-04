"""Interactive PDF Knowledge Base RAG app - reference solution.

Pipeline:
    PDF -> PyPDFLoader -> RecursiveCharacterTextSplitter(1000/200)
        -> OpenAIEmbeddings(text-embedding-3-small) -> Chroma (persistent)
        -> retriever(k=3) -> grounded prompt -> ChatOpenAI(gpt-4o-mini, temp=0)
        -> answer + de-duplicated source pages

Run from this folder:  python rag_app.py
Type 'exit' to quit.
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --------------------------------------------------------------------------- #
#  Configuration                                                               #
# --------------------------------------------------------------------------- #
HERE = os.path.dirname(os.path.abspath(__file__))
LAB_ROOT = os.path.dirname(HERE)

PDF_PATH = os.path.join(LAB_ROOT, "04_DATA", "sample_knowledge_base.pdf")
CHROMA_PATH = os.path.join(LAB_ROOT, "chroma_db")
COLLECTION = "pdf_kb"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
RETRIEVAL_K = 3
CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"
REFUSAL = "I could not find the answer in the provided document."

PROMPT = ChatPromptTemplate.from_template(
    """You are a PDF question-answering assistant.

Answer the question using ONLY the information in the context below.
Do not use outside knowledge.
If the answer cannot be found in the context, reply exactly:
"{refusal}"

Context:
{context}

Question:
{question}

Answer:"""
)


def build_vectorstore(embeddings: OpenAIEmbeddings) -> Chroma:
    """Load the persisted store if present, else build it once from the PDF."""
    if os.path.isdir(CHROMA_PATH) and os.listdir(CHROMA_PATH):
        print("Loading existing Chroma store...")
        return Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings,
            collection_name=COLLECTION,
        )

    print("Building Chroma store from PDF (first run)...")
    documents = PyPDFLoader(PDF_PATH).load()
    print(f"  loaded {len(documents)} pages")
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    ).split_documents(documents)
    print(f"  split into {len(chunks)} chunks")
    return Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH,
        collection_name=COLLECTION,
    )


def answer(question: str, retriever, llm) -> tuple[str, list]:
    docs = retriever.invoke(question)
    context = "\n\n".join(d.page_content for d in docs)
    messages = PROMPT.format_messages(
        refusal=REFUSAL, context=context, question=question
    )
    response = llm.invoke(messages)
    pages = sorted({d.metadata.get("page", "?") for d in docs})
    return response.content.strip(), pages


def main() -> int:
    load_dotenv(os.path.join(LAB_ROOT, "05_CONFIG", ".env"))
    if not os.getenv("OPENAI_API_KEY", "").startswith("sk-"):
        print("OPENAI_API_KEY is not configured. Contact the lab administrator.")
        return 1
    if not os.path.isfile(PDF_PATH):
        print(f"PDF not found: {PDF_PATH}")
        return 1

    embeddings = OpenAIEmbeddings(model=EMBED_MODEL)
    vectorstore = build_vectorstore(embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_K})
    llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)

    print("\nPDF Knowledge Base RAG. Ask a question, or type 'exit'.\n")
    while True:
        try:
            question = input("Question> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() == "exit":
            break
        ans, pages = answer(question, retriever, llm)
        print(f"\nAnswer: {ans}")
        print(f"Sources (pages): {pages}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
