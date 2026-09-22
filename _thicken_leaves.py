# -*- coding: utf-8 -*-
"""Post-enrich: merge ultra-thin leaves, strip boiler, reinject HTML."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
TREE = ROOT / "mindmap-tree.json"
BOILER = (
    "管端侧链路里这一段",
    "别把目录当正文",
    "落在「",
    "见原文档对应小节",
    "先弄清它解决哪类问题",
    "先立章目标，再进主题",
    "给学习路径一个章节锚点",
    "承接「",
    "面向 NVIDIA GPU 的推理栈",
    "面向 NVIDIA GPU 的高性能推理栈",
)


def clip(s: str, n: int = 1800) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def main() -> None:
    tree = json.loads(TREE.read_text(encoding="utf-8"))
    merged = 0
    filled = 0
    for c1 in tree.get("kids") or []:
        for c2 in c1.get("kids") or []:
            parent = c2.get("d") or ""
            paras = [p.strip() for p in parent.split("\n\n") if p.strip()]
            kids = c2.get("kids") or []
            kept: list[dict] = []
            for leaf in kids:
                d = leaf.get("d") or ""
                bare = re.sub(r"^\d+(?:\.\d+)*\s*·\s*", "", leaf.get("t") or "")
                is_boiler = any(b in d for b in BOILER)
                is_thin = len(d) < 50 or d.strip() == bare or is_boiler
                # never fold away a ###-sourced leaf (title is the section anchor)
                if leaf.get("_from_h3"):
                    is_thin = is_boiler and len(d) < 30
                if is_thin and kept and len(kept[-1].get("d") or "") >= 40 and not leaf.get("_from_h3"):
                    # fold into previous sibling
                    prev = kept[-1]
                    chunk = d if d and not is_boiler and d != bare else bare
                    prev["d"] = clip((prev.get("d") or "") + "\n\n" + chunk)
                    merged += 1
                    continue
                if is_thin:
                    keys = [w for w in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", bare) if len(w) >= 2][:5]
                    hit = ""
                    for p in paras:
                        if keys and sum(1 for k in keys if k in p) >= 1:
                            hit = p
                            break
                    if not hit and paras:
                        hit = max(paras, key=len)
                    if hit:
                        leaf["d"] = clip(hit if is_boiler or len(d) < 20 else d + "\n\n" + hit)
                        filled += 1
                kept.append(leaf)
            # renumber leaf titles after merge
            for i, leaf in enumerate(kept, 1):
                bare = re.sub(r"^\d+(?:\.\d+)*\s*·\s*", "", leaf.get("t") or "")
                # keep existing teaching number prefix pattern from parent id
                m = re.match(r"^(\d+(?:\.\d+)*)", c2.get("t") or "")
                prefix = m.group(1) if m else ""
                leaf["t"] = f"{prefix}.{i} · {bare}" if prefix else f"{i} · {bare}"
                leaf["id"] = f"{c2['id']}-{i}"
                leaf.pop("_from_h3", None)
            c2["kids"] = kept

    payload = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
    TREE.write_text(payload, encoding="utf-8")

    import _enrich_content_v2 as e

    for p in e.HTMLS:
        if p.exists():
            e.inject(p, payload)

    leaves = [c3 for c1 in tree["kids"] for c2 in c1.get("kids") or [] for c3 in c2.get("kids") or []]
    lens = sorted(len(x.get("d") or "") for x in leaves)
    thin = sum(1 for n in lens if n < 60)
    boiler = sum(1 for x in leaves if any(b in (x.get("d") or "") for b in BOILER))
    print(
        f"merged={merged} filled={filled} L3={len(leaves)} "
        f"p50={lens[len(lens)//2]} p90={lens[int(len(lens)*0.9)]} "
        f"mean={int(sum(lens)/len(leaves))} thin<60={thin}({100*thin/len(leaves):.1f}%) "
        f"boiler={boiler} chars={sum(lens)}"
    )


if __name__ == "__main__":
    main()
