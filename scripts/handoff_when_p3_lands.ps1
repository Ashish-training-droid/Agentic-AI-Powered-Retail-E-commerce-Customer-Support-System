<#
.SYNOPSIS
    One-shot Pallavi (Person 3) handoff for the Rohan (Person 5) module.

.DESCRIPTION
    Run this AS SOON AS Pallavi (Person 3)'s PR lands on origin/main:

      1. Fetch + rebase the current branch onto origin/main.
      2. Re-run the Rohan (Person 5) unit tests (must stay green — schema is the contract).
      3. Re-run the full evaluation harness against the new real data.
      4. Snapshot the new metrics into tests/evaluation/report_v2.json/.md.
      5. Diff v1 vs v2 into tests/evaluation/report_v1_vs_v2.md (slide 16).

    Safe to run even if you have local commits — uses rebase, not reset.

.EXAMPLE
    pwsh ./scripts/handoff_when_p3_lands.ps1
#>

$ErrorActionPreference = "Stop"

function Step($title) {
    Write-Host ""
    Write-Host ("=" * 72) -ForegroundColor Cyan
    Write-Host "  $title" -ForegroundColor Cyan
    Write-Host ("=" * 72) -ForegroundColor Cyan
}

# Make sure Git is on PATH for this session (matches the user's install location).
$gitPath = "$env:LOCALAPPDATA\Programs\Git\cmd"
if (Test-Path $gitPath) { $env:Path = "$gitPath;" + $env:Path }

# Use mock mode unless the caller already set it; deterministic numbers are
# what we want in a baseline.
if (-not $env:USE_MOCK) { $env:USE_MOCK = "true" }

Step "1/5  Fetch + prune origin"
git fetch --all --prune

$currentBranch = git branch --show-current
Write-Host "Current branch: $currentBranch"

Step "2/5  Rebase $currentBranch onto origin/main"
git rebase origin/main
if ($LASTEXITCODE -ne 0) {
    Write-Host "Rebase failed. Resolve conflicts then re-run this script." -ForegroundColor Red
    exit 1
}

Step "3/5  Run Rohan (Person 5) unit + integration tests"
python -m pytest tests/test_escalation.py tests/test_grounding.py tests/test_router.py -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests failed after rebase. Investigate before regenerating reports." -ForegroundColor Red
    exit 1
}

Step "4/5  Run the evaluation harness and snapshot report_v2"
python -m tests.evaluation.run_evaluation --output tests/evaluation/report_v2.json
python -m tests.evaluation.evaluation_report --input tests/evaluation/report_v2.json --output tests/evaluation/report_v2.md

Step "5/5  Diff v1 vs v2 into report_v1_vs_v2.md (slide 16 source)"
python scripts/compare_reports.py `
    --v1 tests/evaluation/report_v1.json `
    --v2 tests/evaluation/report_v2.json `
    --output tests/evaluation/report_v1_vs_v2.md

Write-Host ""
Write-Host "Handoff complete. Drop the v1 vs v2 table into slide 16 and you're done." -ForegroundColor Green
