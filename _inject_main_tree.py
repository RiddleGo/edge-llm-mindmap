# -*- coding: utf-8 -*-
"""Inject mindmap-tree.json into TREE_MAIN in HTML (no enrich rewrite)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
TREE = ROOT / "mindmap-tree.json"
HTMLS = [ROOT / "端侧部署思维导图.html", ROOT / "index.html"]


def inject(path: Path, payload: str) -> None:
    html = path.read_text(encoding="utf-8")
    marker = None
    for cand in ("const TREE_MAIN = ", "const TREE = ", "const TREE="):
        if cand in html:
            marker = cand
            break
    if marker is None:
        raise SystemExit(f"TREE not found in {path.name}")
    start = html.find(marker)
    eq = html.find("=", start)
    i = eq + 1
    while i < len(html) and html[i] in " \n\r\t":
        i += 1
    if html[i] != "{":
        raise SystemExit(f"expected {{ in {path.name}")
    depth = 0
    in_str = False
    esc = False
    j = i
    while j < len(html):
        ch = html[j]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
        j += 1
    k = j
    while k < len(html) and html[k] in " \t":
        k += 1
    if k < len(html) and html[k] == ";":
        k += 1
    decl = "const TREE_MAIN = " if "TREE_MAIN" in marker else "const TREE = "
    path.write_text(html[:start] + decl + payload + ";" + html[k:], encoding="utf-8")
    print("injected", path.name, path.stat().st_size)


def main() -> None:
    tree = json.loads(TREE.read_text(encoding="utf-8"))
    # light teaching fields without rewriting prose
    for c1 in tree.get("kids") or []:
        for c2 in c1.get("kids") or []:
            if not (c2.get("w") or "").strip():
                bare = c2.get("t") or ""
                c2["w"] = f"本节对应文档小节，右侧正文来自原稿。"
            for leaf in c2.get("kids") or []:
                if not (leaf.get("w") or "").strip():
                    leaf["w"] = "弄清这一点，面试/落地时才知道该动哪一环。"
                leaf.setdefault("b", "")
                leaf.setdefault("k", 0)
            c2.setdefault("b", "")
            c2.setdefault("k", 0)
        c1.setdefault("w", "给学习路径一个章节锚点。")
        c1.setdefault("b", "")
        c1.setdefault("k", 0)
    payload = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
    TREE.write_text(payload, encoding="utf-8")
    for p in HTMLS:
        if p.exists():
            inject(p, payload)


if __name__ == "__main__":
    main()
