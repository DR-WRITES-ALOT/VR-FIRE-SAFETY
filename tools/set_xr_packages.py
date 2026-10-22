#!/usr/bin/env python3
"""Switch the project between "VR" and "desktop-only" packages.

The trainer itself never needs the XR packages: it reads the headset pose, thumbsticks
and trigger through UnityEngine.XR, which ships with the editor in the `xr` module.
The XR packages are only needed to *configure* a headset (OpenXR loader, XR
Interaction Toolkit samples such as the device simulator).

That makes it safe to open the project with the XR packages removed, which is the
quickest way past an editor that crashes while importing them (for example the
"AssetImportWorkerHW0 has crashed" stack inside OpenXR's folder creation).

    python3 tools/set_xr_packages.py desktop    # remove XRI / XR Management / OpenXR
    python3 tools/set_xr_packages.py vr         # put them back (default state)
    python3 tools/set_xr_packages.py status     # show what is in Packages/manifest.json

After running it, close Unity (if it is open), delete the `Library/` folder and reopen
the project so the package list is resolved from scratch.
"""

from __future__ import annotations

import json
import os
import sys

from unity_common import ROOT

MANIFEST = os.path.join(ROOT, "Packages", "manifest.json")

# Versions are the ones used by public projects committed with Unity 6000.5.3f1.
XR_PACKAGES = {
    "com.unity.xr.interaction.toolkit": "3.5.1",
    "com.unity.xr.management": "4.5.4",
    "com.unity.xr.openxr": "1.17.1",
}


def load():
    with open(MANIFEST, encoding="utf-8") as handle:
        return json.load(handle)


def save(manifest):
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def write(mode):
    manifest = load()
    deps = manifest.setdefault("dependencies", {})
    if mode == "vr":
        for package, version in XR_PACKAGES.items():
            deps[package] = version
    elif mode == "desktop":
        for package in XR_PACKAGES:
            deps.pop(package, None)
    else:
        raise SystemExit("unknown mode: %s" % mode)

    # Unity writes modules last; keeping that order makes diffs readable.
    manifest["dependencies"] = dict(
        sorted(deps.items(), key=lambda item: (not item[0].startswith("com.unity.modules"), item[0])))
    save(manifest)
    return manifest["dependencies"]


def main(argv):
    mode = argv[1] if len(argv) > 1 else "status"

    if mode == "status":
        deps = load().get("dependencies", {})
        present = [package for package in XR_PACKAGES if package in deps]
        print("XR packages present: %s" % (", ".join(present) if present else "none (desktop-only)"))
        for package in present:
            print("  %s %s" % (package, deps[package]))
        print("The trainer runs either way; the packages are only needed to configure a headset.")
        return 0

    if mode not in ("vr", "desktop"):
        print(__doc__)
        return 2

    deps = write(mode)
    print("Packages/manifest.json is now in '%s' mode." % mode)
    kept = ", ".join(sorted(p for p in XR_PACKAGES if p in deps)) or "none"
    print("XR packages: %s" % kept)
    print("\nClose Unity, delete the Library/ folder, then reopen the project.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
