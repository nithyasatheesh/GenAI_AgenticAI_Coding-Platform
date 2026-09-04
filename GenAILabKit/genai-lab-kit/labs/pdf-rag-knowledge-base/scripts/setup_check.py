"""Environment preflight for the PDF-RAG lab.

Run:  python scripts/setup_check.py           # offline checks
      python scripts/setup_check.py --live     # also make one tiny API call

Exit codes: 0 = ready, 1 = something missing.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAB_ROOT = os.path.dirname(HERE)

# import-name -> friendly (pip) name
REQUIRED_IMPORTS = {
    "langchain": "langchain",
    "langchain_openai": "langchain-openai",
    "langchain_community": "langchain-community",
    "langchain_text_splitters": "langchain-text-splitters",
    "langchain_chroma": "langchain-chroma",
    "chromadb": "chromadb",
    "pypdf": "pypdf",
    "dotenv": "python-dotenv",
    "ipykernel": "ipykernel",
}
DATA_FILES = [
    "04_DATA/sample_knowledge_base.pdf",
    "04_DATA/RAG_Question_Set.pdf",
]

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def _ok(msg):
    print(f"  {GREEN}PASS{RESET}  {msg}")


def _fail(msg):
    print(f"  {RED}FAIL{RESET}  {msg}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="make one minimal embeddings API call to prove the key works")
    args = ap.parse_args()

    print("PDF-RAG lab - environment preflight")
    print(f"{DIM}lab root: {LAB_ROOT}{RESET}\n")
    failures = 0

    # 1. packages
    print("Packages:")
    for mod, pip_name in REQUIRED_IMPORTS.items():
        if importlib.util.find_spec(mod) is None:
            _fail(f"{pip_name}  (import '{mod}' not found)")
            failures += 1
        else:
            _ok(pip_name)

    # 2. .env / API key
    print("\nConfiguration:")
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(LAB_ROOT, "05_CONFIG", ".env"))
    except Exception:
        pass
    key = os.getenv("OPENAI_API_KEY", "")
    if key.startswith("sk-") and "REPLACE" not in key:
        _ok("OPENAI_API_KEY is set")
    else:
        _fail("OPENAI_API_KEY not configured - contact the lab administrator")
        failures += 1

    # 3. data
    print("\nData files:")
    for rel in DATA_FILES:
        if os.path.isfile(os.path.join(LAB_ROOT, rel)):
            _ok(rel)
        else:
            _fail(f"missing: {rel}")
            failures += 1

    # 4. optional live call
    if args.live and not failures:
        print("\nLive API check:")
        try:
            from langchain_openai import OpenAIEmbeddings
            vec = OpenAIEmbeddings(model="text-embedding-3-small").embed_query("ping")
            _ok(f"embeddings call succeeded (dim={len(vec)})")
        except Exception as exc:  # noqa: BLE001
            _fail(f"embeddings call failed: {exc}")
            failures += 1
    elif args.live:
        print("\nLive API check: skipped (fix the failures above first)")

    print()
    if failures:
        print(f"{RED}{failures} check(s) failed.{RESET} Do not start the lab yet.")
        return 1
    print(f"{GREEN}ALL CHECKS PASSED{RESET} - you're ready. Open the participant notebook.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
