#!/usr/bin/env python3
"""sync_work.py -- Synchronize, track, and push repository changes.

Supports two focused work modes:
  1. manuscript : Recompiles thesis.pdf via compile.sh, calculates chapter word counts,
                  updates MANUSCRIPT.md, stages manuscript files + PDF, and pushes to git.
  2. hardware   : Computes Run 2 day index (from sowing date 2026-10-29), checks local
                  telemetry rows, updates HANDOFF.md, stages hardware/telemetry, and pushes.
  3. auto       : Inspects git status and automatically synchronizes the relevant section
                  (or both if both have changes).

Usage:
  ./sync_work.sh manuscript "revised chapter 3 calibration section"
  ./sync_work.sh hardware "daily checkin D15 - all pots in band"
  ./sync_work.sh auto "sync general updates"
"""

import argparse
import datetime as dt
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MANUSCRIPT_DIR = os.path.join(REPO_ROOT, "2026-11-11-GroupB-Manuscript-Draft1")
MANUSCRIPT_MD = os.path.join(REPO_ROOT, "MANUSCRIPT.md")
HANDOFF_MD = os.path.join(REPO_ROOT, "HANDOFF.md")
SOWING_DATE = dt.date(2026, 10, 29)
HARVEST_DATE = SOWING_DATE + dt.timedelta(days=29)  # Day 30 = Nov 27, 2026


def run(cmd, cwd=REPO_ROOT, check=True):
    """Run shell command and return stdout."""
    res = subprocess.run(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed (exit {res.returncode}):\n{cmd}\n{res.stderr.strip() or res.stdout.strip()}")
    return res.stdout.strip(), res.stderr.strip(), res.returncode


def count_tex_words(file_path):
    """Count words in a LaTeX file, excluding comments and raw commands."""
    if not os.path.exists(file_path):
        return 0
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    # Strip comments
    text = re.sub(r"%.*", "", text)
    # Strip commands
    text = re.sub(r"\\[a-zA-Z]+(\[.*?\])?(\{.*?\})?", " ", text)
    words = re.findall(r"\b[a-zA-Z0-9_\-]+\b", text)
    return len(words)


def get_pdf_page_count(pdf_path):
    """Retrieve PDF page count using mdls on macOS or basic fallback."""
    if not os.path.exists(pdf_path):
        return 0
    out, _, code = run(f"mdls -name kMDItemNumberOfPages '{pdf_path}'", check=False)
    m = re.search(r"=\s*(\d+)", out)
    if m:
        return int(m.group(1))
    return 0


def detect_modified_scopes():
    """Detect which scopes have modified or untracked changes in git."""
    out, _, _ = run("git status --porcelain", check=False)
    manuscript_changed = False
    hardware_changed = False

    for line in out.splitlines():
        if not line.strip():
            continue
        filepath = line[3:].strip()
        if "2026-11-11-GroupB-Manuscript-Draft1" in filepath or filepath in ("MANUSCRIPT.md", "REVISION_LETTER.md"):
            manuscript_changed = True
        elif "Dual_Archi" in filepath or "_pi_data" in filepath or "DATA" in filepath or filepath in ("HANDOFF.md", ".pi_host.sh", "check_system.sh", "daily_checkin.sh", "system.sh"):
            hardware_changed = True

    return manuscript_changed, hardware_changed


# ==============================================================================
# MANUSCRIPT WORKFLOW
# ==============================================================================
def sync_manuscript(message=None):
    print("\n\033[1;36m=== [1/3] Compiling LaTeX Manuscript (compile.sh) ===\033[0m")
    compile_script = os.path.join(MANUSCRIPT_DIR, "compile.sh")
    t0 = dt.datetime.now()
    out, err, code = run(f"bash '{compile_script}'", cwd=MANUSCRIPT_DIR, check=False)
    compile_dur = (dt.datetime.now() - t0).total_seconds()

    pdf_path = os.path.join(MANUSCRIPT_DIR, "thesis.pdf")
    pages = get_pdf_page_count(pdf_path)

    if code == 0 and os.path.exists(pdf_path):
        print(f"\033[0;32m✔ Tectonic compilation succeeded in {compile_dur:.1f}s ({pages} pages generated)\033[0m")
    else:
        print(f"\033[0;31m✘ Compilation failed with exit code {code}!\033[0m")
        print(err[-500:] if err else out[-500:])
        sys.exit(1)

    print("\n\033[1;36m=== [2/3] Analyzing Chapter Word Counts ===\033[0m")
    chapters = {
        "Chapter 1 (Introduction & Scope)": os.path.join(MANUSCRIPT_DIR, "Chapter1/chapter1.tex"),
        "Chapter 2 (Literature Review)": os.path.join(MANUSCRIPT_DIR, "Chapter2/chapter2.tex"),
        "Chapter 3 (Methodology & Bench Design)": os.path.join(MANUSCRIPT_DIR, "Chapter3/chapter3.tex"),
        "Chapter 4 (Results & Discussion)": os.path.join(MANUSCRIPT_DIR, "Chapter4/chapter4.tex"),
        "Chapter 5 (Conclusions & Recommendations)": os.path.join(MANUSCRIPT_DIR, "Chapter5/chapter5.tex"),
    }
    counts = {}
    total_words = 0
    for name, path in chapters.items():
        w = count_tex_words(path)
        counts[name] = w
        total_words += w
        print(f"  {name:42}: {w:>5} words")
    print(f"  \033[1m{'Total Words Across Chapters':42}: {total_words:>5} words ({pages} pages)\033[0m")

    # Update MANUSCRIPT.md Section 8 Timestamp
    now_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if os.path.exists(MANUSCRIPT_MD):
        with open(MANUSCRIPT_MD, "r", encoding="utf-8") as f:
            content = f.read()

        status_block = (
            f"| Metric | Current Value |\n"
            f"| :--- | :--- |\n"
            f"| **Last Compilation** | `{now_str}` (Passing, {pages} pages in {compile_dur:.1f}s) |\n"
            f"| **Chapter 1 Words** | {counts['Chapter 1 (Introduction & Scope)']} words |\n"
            f"| **Chapter 2 Words** | {counts['Chapter 2 (Literature Review)']} words |\n"
            f"| **Chapter 3 Words** | {counts['Chapter 3 (Methodology & Bench Design)']} words |\n"
            f"| **Chapter 4 Words** | {counts['Chapter 4 (Results & Discussion)']} words (Run 2 in progress) |\n"
            f"| **Total Chapters Word Count** | **{total_words} words** ({pages} pages) |\n"
        )

        # Look for ## 8. Current Chapter Status or append
        if "### 8.1 Live Compilation & Word Count Metrics" in content:
            content = re.sub(
                r"### 8\.1 Live Compilation & Word Count Metrics\n.*?(?=\n## |\Z)",
                f"### 8.1 Live Compilation & Word Count Metrics\n\n{status_block}\n",
                content,
                flags=re.DOTALL,
            )
        else:
            content += f"\n\n### 8.1 Live Compilation & Word Count Metrics\n\n{status_block}\n"

        with open(MANUSCRIPT_MD, "w", encoding="utf-8") as f:
            f.write(content)
        print("\033[0;32m✔ Updated MANUSCRIPT.md with live build metrics.\033[0m")

    print("\n\033[1;36m=== [3/3] Staging and Committing Manuscript Changes ===\033[0m")
    run("git add 2026-11-11-GroupB-Manuscript-Draft1 MANUSCRIPT.md REVISION_LETTER.md .vscode/settings.json .gitignore")
    commit_msg = message if message else f"docs(manuscript): sync manuscript chapters and live pdf ({pages} pages, {total_words} words)"
    run(f'git commit -m "{commit_msg}"', check=False)
    print(f"\033[0;32m✔ Committed: {commit_msg}\033[0m")

    print("\n\033[1;36m=== Pushing to origin/main ===\033[0m")
    run("git push origin main")
    print("\033[0;32m✔ Successfully pushed manuscript updates to GitHub!\033[0m")


# ==============================================================================
# HARDWARE / SYSTEM WORKFLOW
# ==============================================================================
def sync_hardware(message=None):
    today = dt.date.today()
    day_num = (today - SOWING_DATE).days + 1
    days_left = max(0, (HARVEST_DATE - today).days)
    now_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n\033[1;36m=== [1/3] AgriSentry Run 2 Status: Day {day_num} of 30 ===\033[0m")
    print(f"  Sowing date: {SOWING_DATE} (D1)")
    print(f"  Today:       {today} (Day {day_num})")
    print(f"  Harvest:     {HARVEST_DATE} (Day 30, {days_left} days remaining)")

    # Read local telemetry rows in _pi_data or DATA if present
    sm_rows = 0
    gpr_rows = 0
    sm_path = os.path.join(REPO_ROOT, "_pi_data/agrisentry_data/sm_log.csv")
    if not os.path.exists(sm_path):
        sm_path = os.path.join(REPO_ROOT, "DATA/agrisentry_data/sm_log.csv")
    if os.path.exists(sm_path):
        with open(sm_path) as f:
            sm_rows = max(0, sum(1 for _ in f) - 1)

    gpr_path = os.path.join(REPO_ROOT, "_pi_data/Dual_Archi/growth_dataset.csv")
    if not os.path.exists(gpr_path):
        gpr_path = os.path.join(REPO_ROOT, "DATA/thesis/growth_dataset.csv")
    if os.path.exists(gpr_path):
        with open(gpr_path) as f:
            gpr_rows = max(0, sum(1 for _ in f) - 1)

    print(f"  Local telemetry: {sm_rows} soil moisture rows, {gpr_rows} GPR daily rows logged.")

    print("\n\033[1;36m=== [2/3] Updating HANDOFF.md ===\033[0m")
    if os.path.exists(HANDOFF_MD):
        with open(HANDOFF_MD, "r", encoding="utf-8") as f:
            handoff = f.read()

        # Append entry to Recent Updates
        entry = (
            f"\n- **Sync Check ({now_str}) -- Day {day_num} of 30:**\n"
            f"  - Run 2 timeline: {days_left} days remaining until harvest on {HARVEST_DATE}.\n"
            f"  - Local data mirror: {sm_rows} soil moisture readings, {gpr_rows} canopy GPR rows.\n"
            f"  - Notes: {message if message else 'Routine daily handoff sync.'}\n"
        )

        if "## Daily Sync & Field Log History" in handoff:
            handoff = handoff.replace("## Daily Sync & Field Log History\n", f"## Daily Sync & Field Log History\n{entry}")
        else:
            handoff += f"\n\n## Daily Sync & Field Log History\n{entry}"

        with open(HANDOFF_MD, "w", encoding="utf-8") as f:
            f.write(handoff)
        print("\033[0;32m✔ Updated HANDOFF.md with latest run status.\033[0m")

    print("\n\033[1;36m=== [3/3] Staging and Committing Hardware Changes ===\033[0m")
    run("git add HANDOFF.md check_system.sh tools .pi_host.sh sync_work.sh daily_checkin.sh system.sh sync_pi.sh")
    if os.path.exists(os.path.join(REPO_ROOT, "_pi_data")):
        run("git add _pi_data", check=False)
    if os.path.exists(os.path.join(REPO_ROOT, "Dual_Archi")):
        run("git add Dual_Archi", check=False)

    commit_msg = message if message else f"sys(hardware): update handoff and system telemetry [D{day_num} - {today}]"
    run(f'git commit -m "{commit_msg}"', check=False)
    print(f"\033[0;32m✔ Committed: {commit_msg}\033[0m")

    print("\n\033[1;36m=== Pushing to origin/main ===\033[0m")
    run("git push origin main")
    print("\033[0;32m✔ Successfully pushed hardware & handoff updates to GitHub!\033[0m")


# ==============================================================================
# MAIN ROUTINE
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Synchronize, document, and push thesis changes.")
    parser.add_argument("mode", nargs="?", default="auto", choices=["manuscript", "hardware", "auto", "all"],
                        help="Target workflow mode (manuscript, hardware, auto, all)")
    parser.add_argument("message", nargs="?", default=None, help="Custom git commit message")
    args = parser.parse_args()

    mode = args.mode.lower()
    if mode == "auto":
        man_changed, hw_changed = detect_modified_scopes()
        if man_changed and not hw_changed:
            mode = "manuscript"
        elif hw_changed and not man_changed:
            mode = "hardware"
        elif man_changed and hw_changed:
            mode = "all"
        else:
            print("\033[1;33mNo modified files detected. What would you like to sync?\033[0m")
            mode = "manuscript"

    if mode in ("manuscript", "all"):
        sync_manuscript(args.message)
    if mode in ("hardware", "all"):
        sync_hardware(args.message)


if __name__ == "__main__":
    main()
