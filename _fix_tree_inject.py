# -*- coding: utf-8 -*-
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\推理VS训练")
html_path = ROOT / "端侧部署思维导图.html"
tree = json.loads((ROOT / "mindmap-tree.json").read_text(encoding="utf-8"))
payload = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))

# Sanity: payload must parse
json.loads(payload)
print("payload ok", len(payload), "}; in payload", payload.count("};"))

html = html_path.read_text(encoding="utf-8")
start = html.find("const TREE = ")
if start < 0:
    raise SystemExit("const TREE not found")
# Find matching end: after '=', skip space, parse JSON with raw_decode
eq = html.find("=", start)
i = eq + 1
while i < len(html) and html[i] in " \n\r\t":
    i += 1
try:
    obj, end = json.JSONDecoder().raw_decode(html, i)
    print("old tree parsed, end", end, "L1", len(obj.get("kids") or []))
except json.JSONDecodeError as e:
    print("old tree broken:", e)
    # salvage: replace from const TREE to next ';\n' after huge blob using brace match
    end = None

# Robust replace: from 'const TREE = ' through end of JSON value + optional ';'
if end is None:
    # brace matching from first {
    assert html[i] == "{"
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
    end = j
    print("brace-matched end", end)

# consume trailing ;
k = end
while k < len(html) and html[k] in " \t":
    k += 1
if k < len(html) and html[k] == ";":
    k += 1

new_html = html[:start] + "const TREE = " + payload + ";" + html[k:]
# verify
i2 = new_html.find("const TREE = ") + len("const TREE = ")
while new_html[i2] in " \n":
    i2 += 1
obj2, _ = json.JSONDecoder().raw_decode(new_html, i2)
print("new tree ok L1", len(obj2["kids"]), "sample k", obj2["kids"][0]["kids"][0].get("k"))
print("frontend intact", all(x in new_html for x in ["key-1", "explain-block", "知识点", "map-legend", "explainBlock"]))
html_path.write_text(new_html, encoding="utf-8")
print("wrote", html_path.stat().st_size)
