#!/usr/bin/env python3
"""
Lightweight file watcher for the manuscript.
Automatically recompiles thesis.pdf whenever any .tex or .bib file changes.
"""

import os
import subprocess
import sys
import time

WATCH_DIR = os.path.dirname(os.path.abspath(__file__))
COMPILE_SCRIPT = os.path.join(WATCH_DIR, "compile.sh")

def get_mtimes():
    mtimes = {}
    for root, _, files in os.walk(WATCH_DIR):
        if ".git" in root or "unused-files" in root:
            continue
        for f in files:
            if f.endswith((".tex", ".bib")):
                path = os.path.join(root, f)
                try:
                    mtimes[path] = os.path.getmtime(path)
                except OSError:
                    pass
    return mtimes

def main():
    print(f"[*] Watching {WATCH_DIR} for changes in .tex and .bib files...")
    last_mtimes = get_mtimes()
    
    while True:
        time.sleep(1.0)
        current_mtimes = get_mtimes()
        changed = []
        for path, mtime in current_mtimes.items():
            if path not in last_mtimes or mtime > last_mtimes[path]:
                changed.append(os.path.basename(path))
        
        if changed:
            print(f"[!] Change detected in: {', '.join(changed)}. Recompiling...")
            last_mtimes = current_mtimes
            try:
                subprocess.run(["bash", COMPILE_SCRIPT], cwd=WATCH_DIR, check=True)
                print("[+] Compilation complete: thesis.pdf updated!")
            except subprocess.CalledProcessError as e:
                print(f"[-] Compilation error: {e}")
            # Refresh mtimes after compile
            last_mtimes = get_mtimes()

if __name__ == "__main__":
    main()
