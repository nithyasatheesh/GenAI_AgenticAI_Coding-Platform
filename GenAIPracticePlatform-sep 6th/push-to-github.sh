#!/usr/bin/env bash
# Force-replace your GitHub repo with THIS folder, then Streamlit Cloud rebuilds.
# Usage (from inside this folder):
#   ./push-to-github.sh https://github.com/<you>/<your-repo>.git
set -euo pipefail

REPO_URL="${1:-}"
[ -z "$REPO_URL" ] && { echo "usage: ./push-to-github.sh https://github.com/<you>/<repo>.git"; exit 1; }
[ -f ./streamlit_app.py ] || { echo "Run from the folder that CONTAINS streamlit_app.py"; exit 1; }

git init
git add -A
git commit -m "practice platform - clean pure-wheel deploy"
git branch -M main
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"
git push -u --force origin main

echo
echo "Pushed. Now in Streamlit Cloud:  Manage app -> Reboot app."
echo "App settings must be:  Repository = that repo,  Branch = main,  Main file path = streamlit_app.py"
