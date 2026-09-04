"""Automated validation for the PDF-RAG lab.

Builds the RAG pipeline (from the reference app), then runs every question in
04_DATA/RAG_Question_Set.pdf:

  * grounded / reasoning questions (1-15) must produce a real answer
    (not the refusal) and cite at least one source page;
  * negative / out-of-context questions (16-20) must return the exact refusal
    sentence.

Run:  python scripts/validate_solution.py            # full, needs the API key
      python scripts/validate_solution.py --offline   # parse + wiring only

Exit codes: 0 = all pass, 1 = failures, 2 = environment not ready.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAB_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(LAB_ROOT, "03_SOLUTION_GUIDE"))

QSET = os.path.join(LAB_ROOT, "04_DATA", "RAG_Question_Set.pdf")
REFUSAL = "I could not find the answer in the provided document."
NEGATIVE_IDS = {16, 17, 18, 19, 20}

GREEN, RED, YELLOW, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


def parse_questions(pdf_path: str) -> list[tuple[int, str]]:
    from pypdf import PdfReader
    text = "\n".join(p.extract_text() or "" for p in PdfReader(pdf_path).pages)
    items = re.findall(r"(?m)^\s*(\d{1,2})\.\s+(.+?)\s*$", text)
    out, seen = [], set()
    for num, q in items:
        n = int(num)
        if 1 <= n <= 20 and n not in seen:
            seen.add(n)
            out.append((n, q.strip()))
    return sorted(out)


def is_refusal(answer: str) -> bool:
    a = answer.lower()
    return "could not find the answer" in a or "cannot be found" in a


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="only parse the question set and check imports/wiring")
    args = ap.parse_args()

    if not os.path.isfile(QSET):
        print(f"{RED}Question set not found: {QSET}{RESET}")
        return 2
    if importlib.util.find_spec("pypdf") is None:
        print(f"{RED}pypdf not installed - run scripts/setup_check.py{RESET}")
        return 2

    questions = parse_questions(QSET)
    print(f"Parsed {len(questions)} questions from RAG_Question_Set.pdf")
    grounded = [q for q in questions if q[0] not in NEGATIVE_IDS]
    negative = [q for q in questions if q[0] in NEGATIVE_IDS]
    print(f"  grounded/reasoning: {len(grounded)}   negative: {len(negative)}\n")

    if len(questions) < 15:
        print(f"{RED}Expected 20 questions - PDF parse looks wrong.{RESET}")
        return 1

    if args.offline:
        try:
            import rag_app  # noqa: F401  (from 03_SOLUTION_GUIDE)
            print(f"{GREEN}offline OK{RESET}: question set parsed, rag_app imports cleanly.")
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"{RED}rag_app import failed:{RESET} {exc}")
            return 1

    # ---- live run ---------------------------------------------------------- #
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(LAB_ROOT, "05_CONFIG", ".env"))
    except Exception:
        pass
    if not os.getenv("OPENAI_API_KEY", "").startswith("sk-"):
        print(f"{YELLOW}OPENAI_API_KEY not configured - run with --offline or set the key.{RESET}")
        return 2

    import rag_app
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(model=rag_app.EMBED_MODEL)
    vectorstore = rag_app.build_vectorstore(embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": rag_app.RETRIEVAL_K})
    llm = ChatOpenAI(model=rag_app.CHAT_MODEL, temperature=0)

    passed = failed = 0
    print("Grounded / reasoning questions (must answer + cite pages):")
    for n, q in grounded:
        ans, pages = rag_app.answer(q, retriever, llm)
        real_pages = [p for p in pages if p != "?"]
        ok = (not is_refusal(ans)) and len(real_pages) > 0
        mark = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  {mark} Q{n:<2} {q[:58]:<58} pages={real_pages}")
        if not ok:
            print(f"        -> {ans[:120]}")
        passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)

    print("\nNegative / out-of-context questions (must refuse):")
    for n, q in negative:
        ans, _ = rag_app.answer(q, retriever, llm)
        ok = is_refusal(ans)
        mark = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  {mark} Q{n:<2} {q[:58]:<58}")
        if not ok:
            print(f"        -> invented an answer: {ans[:120]}")
        passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)

    total = passed + failed
    print(f"\n{'-' * 60}\nResult: {passed}/{total} passed")
    if failed:
        print(f"{RED}{failed} failing - review the prompt grounding and retrieval k.{RESET}")
        return 1
    print(f"{GREEN}Lab solution validated.{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
