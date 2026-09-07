# Force-replace your GitHub repo with THIS folder, then Streamlit Cloud rebuilds.
# Usage (PowerShell, from inside this folder):
#   .\push-to-github.ps1 https://github.com/<you>/<your-repo>.git
param([Parameter(Mandatory=$true)][string]$RepoUrl)

$ErrorActionPreference = "Stop"
if (-not (Test-Path ".\streamlit_app.py")) {
    throw "Run this from the folder that CONTAINS streamlit_app.py (the unzipped bundle root)."
}

git init
git add -A
git commit -m "practice platform - clean pure-wheel deploy"
git branch -M main
git remote remove origin 2>$null
git remote add origin $RepoUrl
git push -u --force origin main

Write-Host ""
Write-Host "Pushed. Now in Streamlit Cloud:  Manage app -> Reboot app." -ForegroundColor Green
Write-Host "App settings must be:  Repository = that repo,  Branch = main,  Main file path = streamlit_app.py"
