"""Environment preflight - TEMPLATE.

Edit REQUIRED_IMPORTS, REQUIRED_ENV and DATA_FILES for this lab, then this script
tells the participant (or the vendor QA) whether the VM is ready.

Run:  python scripts/setup_check.py
Exit codes: 0 = ready, 1 = something missing.
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAB_ROOT = os.path.dirname(HERE)

# import-name -> pip name
REQUIRED_IMPORTS = {
    "dotenv": "python-dotenv",
    # "langchain_openai": "langchain-openai",
}
REQUIRED_ENV = [
    "OPENAI_API_KEY",
]
DATA_FILES: list[str] = [
    # "04_DATA/corpus.pdf",
]

GREEN, RED, RESET = "\033[32m", "\033[31m", "\033[0m"
def _ok(m): print(f"  {GREEN}PASS{RESET}  {m}")
def _fail(m): print(f"  {RED}FAIL{RESET}  {m}")


def main() -> int:
    print(f"Preflight - {os.path.basename(LAB_ROOT)}\n")
    fails = 0

    print("Packages:")
    for mod, pip_name in REQUIRED_IMPORTS.items():
        if importlib.util.find_spec(mod) is None:
            _fail(f"{pip_name} (import '{mod}')"); fails += 1
        else:
            _ok(pip_name)

    print("\nConfiguration:")
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(LAB_ROOT, "05_CONFIG", ".env"))
    except Exception:
        pass
    for name in REQUIRED_ENV:
        val = os.getenv(name, "")
        if val and "REPLACE" not in val:
            _ok(f"{name} is set")
        else:
            _fail(f"{name} not configured - contact the lab administrator"); fails += 1

    if DATA_FILES:
        print("\nData files:")
        for rel in DATA_FILES:
            if os.path.isfile(os.path.join(LAB_ROOT, rel)):
                _ok(rel)
            else:
                _fail(f"missing: {rel}"); fails += 1

    print()
    if fails:
        print(f"{RED}{fails} check(s) failed.{RESET} Do not start the lab yet.")
        return 1
    print(f"{GREEN}ALL CHECKS PASSED{RESET} - you're ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
