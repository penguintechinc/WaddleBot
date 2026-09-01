#!/usr/bin/env python3
"""
Pin npm package.json dependencies to exact versions from package-lock.json.
Removes ^ and ~ ranges, preserving JSON formatting and key order.
"""
import json
import sys
from pathlib import Path


def read_lock_versions(lock_path):
    """Extract exact versions from package-lock.json."""
    with open(lock_path) as f:
        lock = json.load(f)

    versions = {}
    # lockfileVersion 3: packages["node_modules/X"].version
    if "packages" in lock:
        for key, pkg in lock["packages"].items():
            if key.startswith("node_modules/") and "version" in pkg:
                name = key.replace("node_modules/", "")
                versions[name] = pkg["version"]
    return versions


def pin_deps(package_json_path):
    """Pin dependencies/devDependencies to exact versions."""
    with open(package_json_path) as f:
        content = f.read()
        pj = json.loads(content)

    lock_path = package_json_path.parent / "package-lock.json"
    if not lock_path.exists():
        print(f"SKIP {package_json_path}: no package-lock.json")
        return 0

    lock_versions = read_lock_versions(lock_path)
    pinned = 0

    for dep_type in ("dependencies", "devDependencies", "optionalDependencies"):
        if dep_type not in pj:
            continue
        for name, version in pj[dep_type].items():
            if version.startswith("^") or version.startswith("~"):
                if name in lock_versions:
                    pj[dep_type][name] = lock_versions[name]
                    pinned += 1
                else:
                    print(f"WARN {package_json_path}: {name} not in lock")

    if pinned > 0:
        with open(package_json_path, "w") as f:
            json.dump(pj, f, indent=2)
            f.write("\n")
        print(f"PINNED {package_json_path}: {pinned} ranges")
    return pinned


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: pin-npm-versions.py <package.json_path> [...]")
        sys.exit(1)

    total = 0
    for path in sys.argv[1:]:
        total += pin_deps(Path(path))
    print(f"\nTotal pinned: {total}")
