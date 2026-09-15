# -*- coding: utf-8 -*-
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\推理VS训练")
TREE_JSON = ROOT / "mindmap-tree.json"
HTML = ROOT / "端侧部署思维导图.html"

tree = json.loads(TREE_JSON.read_text(encoding="utf-8"))


def clean_d(d: str) -> str:
    d = d or ""
    m = re.search(r"（补充：(.+?)。）", d)
    if not m:
        return d
    extra = m.group(1)
    base = d[: m.start()]
    if extra[:24] in base or sum(1 for a, b in zip(extra[:40], base) if a == b) > 12:
        return base.rstrip("。") + "。"
    return d


n = 0
for c1 in tree.get("kids") or []:
    for c2 in c1.get("kids") or []:
        for leaf in c2.get("kids") or []:
            old = leaf.get("d") or ""
            neu = clean_d(old)
            if neu != old:
                leaf["d"] = neu
                n += 1

payload = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
TREE_JSON.write_text(payload, encoding="utf-8")
print("cleaned", n)

html = HTML.read_text(encoding="utf-8")
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

for a, b in [
    ("讲义 · 是什么 / 作用 / 承接", "讲义 · 是什么 / 作用（承上启下仅主题）"),
    ("讲义 · 是什么 / 作用 / 承接", "讲义 · 是什么 / 作用（承上启下仅主题）"),
    ("是什么 / 作用 / 承接", "是什么 / 作用"),
]:
    html = html.replace(a, b)

# clarify explain block label for bridge
html = html.replace(
    '承上启下</div>',
    '目录承上启下</div>',
)

HTML.write_text(html, encoding="utf-8")
c5 = next(c for c in tree["kids"] if c["t"].startswith("5"))
print(c5["kids"][0]["kids"][0]["d"])
print("html", HTML.stat().st_size)
