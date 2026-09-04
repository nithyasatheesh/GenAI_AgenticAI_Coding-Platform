#!/usr/bin/env bash
# Provision a GenAI Lab Kit VM image (Ubuntu 22.04). Idempotent - safe to re-run.
#
#   sudo ./vm-provisioning/provision.sh
#
# After this, fill each lab's 05_CONFIG/.env and run the per-lab preflight
# (see VM_REQUIREMENTS.md section 5).
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

echo "== GenAI Lab Kit provisioning =="
echo "kit: $KIT_DIR"
echo "python: $($PYTHON --version)"

# 1. system packages
if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y --no-install-recommends \
    "$PYTHON" "${PYTHON}-venv" "${PYTHON}-dev" python3-pip \
    build-essential git curl ca-certificates
fi

# 2. python packages (aggregated across all labs)
REQ="$KIT_DIR/vm-provisioning/requirements.txt"
if [ ! -f "$REQ" ]; then
  echo "!! $REQ missing - generating it now"
  "$PYTHON" "$KIT_DIR/tools/aggregate_requirements.py"
fi
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r "$REQ"

# 3. jupyter kernel
"$PYTHON" -m ipykernel install --name python3 --display-name "Python 3" || true

# 4. per-lab preflight (offline part only - no key needed yet)
echo
echo "== Per-lab offline preflight =="
fail=0
for lab in "$KIT_DIR"/labs/*/; do
  name="$(basename "$lab")"
  if [ -f "$lab/scripts/setup_check.py" ]; then
    echo "--- $name ---"
    if ! ( cd "$lab" && "$PYTHON" scripts/setup_check.py ); then
      # expected to report the missing key until .env is filled
      echo "(note: $name preflight not fully green - fill 05_CONFIG/.env, then re-run with --live)"
      fail=1
    fi
  fi
done

echo
echo "== Done. Next steps =="
echo "  1. For each lab: cp 05_CONFIG/.env.example 05_CONFIG/.env  and add the key"
echo "  2. cd <lab> && $PYTHON scripts/setup_check.py --live"
echo "  3. cd <lab> && $PYTHON scripts/validate_solution.py"
echo "  4. Remove every labs/*/03_SOLUTION_GUIDE/ from the PARTICIPANT image"
[ "$fail" -eq 0 ] && echo "  (all offline preflights passed)" || true
