# -*- coding: utf-8 -*-
"""Rebuild jd-gap-tree.json and refresh TREE_JD inside HTML."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent


def refresh_html_tree_jd() -> None:
    import build_jd_gap_tree as b

    b.main()
    jd = (ROOT / "jd-gap-tree.json").read_text(encoding="utf-8").strip()
    for name in ("端侧部署思维导图.html", "index.html"):
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        m = re.search(r"const TREE_JD = (\{.*?\});", text, re.S)
        if not m:
            raise SystemExit(f"TREE_JD not found in {name}")
        text = text[: m.start()] + "const TREE_JD = " + jd + ";" + text[m.end() :]
        path.write_text(text, encoding="utf-8")
        print("updated TREE_JD in", name, "bytes", path.stat().st_size)


if __name__ == "__main__":
    refresh_html_tree_jd()
