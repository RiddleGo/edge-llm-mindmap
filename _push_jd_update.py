# -*- coding: utf-8 -*-
"""Update GitHub Pages repo via Contents/git API (git HTTPS may be blocked)."""
from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
OWNER = "RiddleGo"
REPO = "edge-llm-mindmap"

# Files that matter for the mind map site
PUSH_PATHS = [
    "index.html",
    "端侧部署思维导图.html",
    "端侧模型部署.md",
    "jd-gap-tree.json",
    "JD能力缺口补全.md",
    "README.md",
    "mindmap-tree.json",
    "维护手册.md",
    "更新网页.py",
    "更新网页.bat",
    ".gitignore",
    "build_mindmap_tree.py",
    "build_jd_gap_tree.py",
    "_enrich_content_v2.py",
    "_thicken_leaves.py",
    "_batch_fill_leaves.py",
    "_refresh_jd_tree.py",
    "_push_jd_update.py",
]


def gh_api(method: str, path: str, body: dict | None = None) -> dict:
    cmd = ["gh", "api", "-X", method, path]
    if body is not None:
        cmd.extend(["--input", "-"])
    p = subprocess.run(
        cmd,
        input=json.dumps(body).encode("utf-8") if body is not None else None,
        capture_output=True,
        cwd=ROOT,
    )
    if p.returncode != 0:
        err = (p.stderr or p.stdout).decode("utf-8", errors="replace")
        raise SystemExit(f"gh api {method} {path} failed:\n{err}")
    out = p.stdout.decode("utf-8")
    return json.loads(out) if out.strip() else {}


def main() -> None:
    ref = gh_api("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/main")
    parent = ref["object"]["sha"]
    print("parent", parent[:8])

    entries = []
    for rel in PUSH_PATHS:
        path = ROOT / rel
        if not path.exists():
            print("skip missing", rel)
            continue
        data = path.read_bytes()
        blob = gh_api(
            "POST",
            f"/repos/{OWNER}/{REPO}/git/blobs",
            {"content": base64.b64encode(data).decode("ascii"), "encoding": "base64"},
        )
        entries.append(
            {"path": rel.replace("\\", "/"), "mode": "100644", "type": "blob", "sha": blob["sha"]}
        )
        print("blob", rel, blob["sha"][:8], "bytes", len(data))

    base_commit = gh_api("GET", f"/repos/{OWNER}/{REPO}/git/commits/{parent}")
    base_tree = base_commit["tree"]["sha"]
    tree = gh_api(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/trees",
        {"base_tree": base_tree, "tree": entries},
    )
    print("tree", tree["sha"][:8])
    commit = gh_api(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/commits",
        {
            "message": "Rebuild mind map from updated JD skill-graph markdown.\n\nParse 一、二、三… chapters into TREE_MAIN and re-inject index.html / 端侧部署思维导图.html for GitHub Pages.",
            "tree": tree["sha"],
            "parents": [parent],
        },
    )
    print("commit", commit["sha"][:8])
    gh_api(
        "PATCH",
        f"/repos/{OWNER}/{REPO}/git/refs/heads/main",
        {"sha": commit["sha"]},
    )
    print("OK https://riddlego.github.io/edge-llm-mindmap/")


if __name__ == "__main__":
    main()
