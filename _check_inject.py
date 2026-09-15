# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\推理VS训练")
tree = json.loads((ROOT / "mindmap-tree.json").read_text(encoding="utf-8"))
html = (ROOT / "端侧部署思维导图.html").read_text(encoding="utf-8")
start = html.find("const TREE = ")
i = html.find("{", start)
obj, end = json.JSONDecoder().raw_decode(html, i)
print("json root d:", tree["d"][:80])
print("html root d:", obj["d"][:80])

def find_ascend(root):
    for c1 in root.get("kids") or []:
        for c2 in c1.get("kids") or []:
            if "昇腾" in (c2.get("t") or ""):
                return c2
    return None

j2 = find_ascend(tree)
h2 = find_ascend(obj)
print("json 昇腾 b:", (j2 or {}).get("b"))
print("html 昇腾 b:", (h2 or {}).get("b"))
print("json vs html same TREE?", tree["d"] == obj["d"] and (j2 or {}).get("b") == (h2 or {}).get("b"))
print("上接 in json?", "上接「" in json.dumps(tree, ensure_ascii=False))
print("上接 in html tree?", "上接「" in json.dumps(obj, ensure_ascii=False))
print("目录承上启下 in html?", "目录承上启下" in html)
