#!/usr/bin/env python3
"""Run every static check in one go.

    python3 tools/check_all.py

Checks:
  verify_scene.py    scene references, GUIDs, serialized fields, .meta files
  verify_flow.py     lesson events, stages, content, colliders, manager wiring
  verify_project.py  editor version, packages, URP wiring, player settings, GUID table
  check_cs_access.py cross-class C# accessibility (the errors a compiler would give)

Every check exits non-zero on failure; this runner stops at the first failure unless
--keep-going is passed, and always prints a summary.
"""

from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS = [
    ("scene structure", "verify_scene.py"),
    ("lesson flow", "verify_flow.py"),
    ("project settings", "verify_project.py"),
    ("C# accessibility", "check_cs_access.py"),
]


def main(argv):
    keep_going = "--keep-going" in argv
    results = []

    for label, script in CHECKS:
        path = os.path.join(HERE, script)
        if not os.path.exists(path):
            results.append((label, "missing", script))
            continue
        print("=== %s (%s)" % (label, script))
        completed = subprocess.run([sys.executable, path], capture_output=True, text=True)
        output = (completed.stdout or "").strip().splitlines()
        for line in output:
            print("    " + line)
        if completed.returncode != 0 and completed.stderr.strip():
            for line in completed.stderr.strip().splitlines():
                print("    ! " + line)
        print()
        results.append((label, "ok" if completed.returncode == 0 else "FAILED", script))
        if completed.returncode != 0 and not keep_going:
            break

    print("=== summary")
    for label, status, script in results:
        print("  %-18s %-7s %s" % (label, status, script))

    failed = [label for label, status, _ in results if status != "ok"]
    if failed:
        print("\n%d check(s) failed: %s" % (len(failed), ", ".join(failed)))
        return 1

    print("\nAll static checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
