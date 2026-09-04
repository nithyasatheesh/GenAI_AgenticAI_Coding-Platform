"""Task 5 - Interactive PDF Knowledge Base RAG app  (STARTER).

Complete every # TODO, then run from this folder:  python rag_app.py
Type 'exit' to quit.

Required settings (do not change):
    chunk_size = 1000, chunk_overlap = 200, k = 3
    chat model = gpt-4o-mini, temperature = 0
    refusal   = "I could not find the answer in the provided document."
"""
import os
import sys

from dotenv import load_dotenv

# --- paths (already correct - do not change) ------------------------------- #
HERE = os.path.dirname(os.path.abspath(__file__))
LAB_ROOT = os.path.dirname(HERE)
PDF_PATH = os.path.join(LAB_ROOT, "04_DATA", "sample_knowledge_base.pdf")
CHROMA_PATH = os.path.join(LAB_ROOT, "chroma_db")
COLLECTION = "pdf_kb"
REFUSAL = "I could not find the answer in the provided document."

# --- TODO 1: imports ----------------------------------------------------- #
# You need: PyPDFLoader, RecursiveCharacterTextSplitter,
#           OpenAIEmbeddings, ChatOpenAI, Chroma, ChatPromptTemplate


def build_vectorstore(embeddings):
    """Load the persisted Chroma store if it exists, otherwise build it once."""
    if os.path.isdir(CHROMA_PATH) and os.listdir(CHROMA_PATH):
        # TODO 2: return an existing Chroma store
        #   Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings,
        #          collection_name=COLLECTION)
        raise NotImplementedError

    # TODO 3: build the store
    #   - load PDF_PATH with PyPDFLoader
    #   - split with RecursiveCharacterTextSplitter(1000, 200)
    #   - return Chroma.from_documents(..., persist_directory=CHROMA_PATH,
    #                                  collection_name=COLLECTION)
    raise NotImplementedError


def answer(question, retriever, llm, prompt):
    # TODO 4:
    #   docs    = retriever.invoke(question)
    #   context = "\n\n".join(d.page_content for d in docs)
    #   msgs    = prompt.format_messages(context=context, question=question)
    #   resp    = llm.invoke(msgs)
    #   pages   = sorted({d.metadata.get("page", "?") for d in docs})
    #   return resp.content.strip(), pages
    raise NotImplementedError


def main():
    load_dotenv(os.path.join(LAB_ROOT, "05_CONFIG", ".env"))
    if not os.getenv("OPENAI_API_KEY", "").startswith("sk-"):
        print("OPENAI_API_KEY is not configured. Contact the lab administrator.")
        return 1

    # TODO 5: create embeddings (text-embedding-3-small)
    embeddings = None

    vectorstore = build_vectorstore(embeddings)

    # TODO 6: retriever with k=3
    retriever = None

    # TODO 7: llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    llm = None

    # TODO 8: grounded prompt with {context} and {question};
    #         must tell the model to answer ONLY from context and, if missing,
    #         reply exactly with REFUSAL.
    prompt = None

    print("\nPDF Knowledge Base RAG. Ask a question, or type 'exit'.\n")
    while True:
        question = input("Question> ").strip()
        if not question:
            continue
        if question.lower() == "exit":
            break
        ans, pages = answer(question, retriever, llm, prompt)
        print(f"\nAnswer: {ans}")
        print(f"Sources (pages): {pages}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
