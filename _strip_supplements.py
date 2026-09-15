# -*- coding: utf-8 -*-
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\推理VS训练")
tree = json.loads((ROOT / "mindmap-tree.json").read_text(encoding="utf-8"))
n = 0
for c1 in tree["kids"]:
    for c2 in c1.get("kids") or []:
        for leaf in c2.get("kids") or []:
            d = leaf.get("d") or ""
            if "（补充：" in d:
                leaf["d"] = re.sub(r"（补充：.*$", "", d).rstrip("。") + "。"
                n += 1
print("stripped", n)
c5 = next(c for c in tree["kids"] if c["t"].startswith("5"))
print(c5["kids"][0]["kids"][0]["d"])
payload = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
(ROOT / "mindmap-tree.json").write_text(payload, encoding="utf-8")

html_path = ROOT / "端侧部署思维导图.html"
html = html_path.read_text(encoding="utf-8")
start = html.find("const TREE = ")
i = html.find("{", start)
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
if k < len(html) and html[k] == ";":
    k += 1
html = html[:start] + "const TREE = " + payload + ";" + html[k:]
html_path.write_text(html, encoding="utf-8")
print("html", html_path.stat().st_size)
