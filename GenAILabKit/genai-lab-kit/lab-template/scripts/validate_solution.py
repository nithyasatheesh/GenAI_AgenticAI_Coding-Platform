"""Automated validation - TEMPLATE.

Import the reference solution from 03_SOLUTION_GUIDE/ and assert the behaviours
the lab promises. Keep it deterministic (temperature=0, fixed seeds).

Run:  python scripts/validate_solution.py [--offline]
Exit codes: 0 = all pass, 1 = failures, 2 = environment not ready.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAB_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(LAB_ROOT, "03_SOLUTION_GUIDE"))

GREEN, RED, RESET = "\033[32m", "\033[31m", "\033[0m"


def checks_offline() -> list[tuple[str, bool]]:
    """Things you can verify without calling any paid API."""
    results = []
    # results.append(("question set parses", ...))
    # results.append(("solution module imports", ...))
    return results


def checks_live() -> list[tuple[str, bool]]:
    """End-to-end assertions against the real pipeline."""
    results = []
    # from solution_module import build_pipeline, answer
    # pipe = build_pipeline()
    # results.append(("grounded question answered", not is_refusal(answer(pipe, Q1))))
    # results.append(("out-of-context question refused", is_refusal(answer(pipe, Qneg))))
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    results = checks_offline()
    if not args.offline:
        try:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(LAB_ROOT, "05_CONFIG", ".env"))
        except Exception:
            pass
        if not os.getenv("OPENAI_API_KEY", "").startswith("sk-"):
            print("OPENAI_API_KEY not set - run with --offline or configure the key.")
            return 2
        results += checks_live()

    if not results:
        print("No checks implemented yet. Fill in checks_offline() / checks_live().")
        return 1

    passed = 0
    for name, ok in results:
        mark = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  {mark}  {name}")
        passed += bool(ok)

    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
