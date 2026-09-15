# -*- coding: utf-8 -*-
"""Build mindmap tree + self-contained HTML."""
import json, re
from pathlib import Path

root = Path(__file__).resolve().parent
md = next(p for p in root.iterdir() if p.name == "端侧模型部署.md")
text = md.read_text(encoding="utf-8")
text = "".join(p if i % 2 == 0 else "" for i, p in enumerate(text.split("```")))

def short(s, n=40):
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[🃏↪⏱↔⏩⚠✅]", "", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"

tree = {"id": "root", "t": "端侧大模型部署", "d": "循序：〇认端侧 → ⑫入门 → ②主链 → ③变轻 → ⑬尺子 → ⑭/⑩平台 → ⑮交付。点击从左到右展开。", "kids": []}
cur1 = cur2 = None
term_re = re.compile(r"^- \*\*(.+?)\*\*\s*[—–:：]\s*(.+)$")
ext_mark = False
l2_from_h2 = False

def new_l1(title):
    global cur1, cur2, ext_mark, l2_from_h2
    cur1 = {"id": f"c{len(tree['kids'])+1}", "t": short(title, 26), "d": "", "kids": []}
    tree["kids"].append(cur1)
    cur2 = None
    ext_mark = title.startswith(("⑬", "⑭", "⑮", "⑯"))
    l2_from_h2 = False

def new_l2(title, from_h2=False):
    global cur2, l2_from_h2
    if not cur1:
        return
    cur2 = {"id": f"{cur1['id']}-{len(cur1['kids'])+1}", "t": short(title, 32), "d": "", "kids": []}
    cur1["kids"].append(cur2)
    l2_from_h2 = from_h2

def add_l3(title, desc=""):
    if not cur2:
        return
    if len(cur2["kids"]) >= 18:
        return
    t = short(title, 26)
    if any(k["t"] == t for k in cur2["kids"]):
        return
    cur2["kids"].append({
        "id": f"{cur2['id']}-{len(cur2['kids'])+1}",
        "t": t,
        "d": short(desc, 96) if desc else "",
        "kids": []
    })

for raw in text.splitlines():
    line = raw.rstrip()
    m0 = re.match(r"^##\s+(〇\s*.+)$", line)
    m1 = re.match(r"^##\s+([①-⑫].+)$", line)
    m1b = re.match(r"^#\s+(⑬|⑭|⑮|⑯)(.*)$", line)
    if m0:
        new_l1(m0.group(1)); continue
    if m1:
        new_l1(m1.group(1)); continue
    if m1b:
        new_l1(m1b.group(1) + m1b.group(2)); continue
    if re.match(r"^##\s+", line) and cur1:
        new_l2(line[3:].strip(), from_h2=True); continue
    if re.match(r"^###\s+", line) and cur1:
        title = line[4:].strip()
        if ext_mark and l2_from_h2 and cur2:
            add_l3(title)
        else:
            new_l2(title, from_h2=False)
        continue
    if not cur1:
        continue
    if not cur2:
        if line and not line.startswith(("#", "|", ">", "-", "*")) and not cur1["d"]:
            cur1["d"] = short(line, 70)
        continue
    tm = term_re.match(line)
    if tm:
        add_l3(tm.group(1), tm.group(2)); continue
    if line.startswith("- "):
        body = line[2:].strip()
        body = re.sub(r"^\*\*(.+?)\*\*\s*", r"\1 ", body)
        add_l3(body[:26], body)

for c in tree["kids"]:
    c["kids"] = [s for s in c["kids"] if s["t"]]
    for s in c["kids"]:
        if not s["kids"]:
            s["kids"].append({"id": s["id"]+"-n", "t": s["t"], "d": s["d"] or "见原文档对应小节", "kids": []})

def renumber_teaching_order(tree):
    """Strip 〇⑫… / old digits; stamp 1 / 1.1 / 1.1.1 by array order (teaching path).

    Note: explanation fields d/w/b and highlight flag k are owned by
    `_enrich_explain.py`. Do not wipe w/b/k here if already present.
    """
    circle = re.compile(r"^(?:〇|①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|⑪|⑫|⑬|⑭|⑮|⑯)(?:-?\d+)?\s*[·.\s、]*\s*")
    num = re.compile(r"^(?:\d+(?:\.\d+){0,3})\s*[·.\s、\-–—]+\s*")
    def strip_old(title):
        t = title.strip()
        t = circle.sub("", t)
        t = num.sub("", t)
        return t.strip(" ·.-–—") or title.strip()
    for i, c1 in enumerate(tree.get("kids") or [], 1):
        c1["t"] = f"{i} · {strip_old(c1.get('t') or '')}"
        # preserve w/b/k if enrich script already filled them
        for j, c2 in enumerate(c1.get("kids") or [], 1):
            c2["t"] = f"{i}.{j} · {strip_old(c2.get('t') or '')}"
            for k, c3 in enumerate(c2.get("kids") or [], 1):
                c3["t"] = f"{i}.{j}.{k} · {strip_old(c3.get('t') or '')}"
    # only set a short root hint if enrich has not already written the full guide
    if "是什么" not in (tree.get("d") or ""):
        tree["d"] = "讲课序号 1→N。章=1；主题=1.1；术语=1.1.1。并排先看序号。"
    return tree

tree = renumber_teaching_order(tree)
TREE_JSON = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
(root / "mindmap-tree.json").write_text(TREE_JSON, encoding="utf-8")
(root / "_tree_stats.txt").write_text(
    f"L1={len(tree['kids'])} L2={sum(len(c['kids']) for c in tree['kids'])} "
    f"L3={sum(len(s['kids']) for c in tree['kids'] for s in c['kids'])}\n"
    + "\n".join(f"{c['t']} L2={len(c['kids'])} L3={sum(len(s['kids']) for s in c['kids'])}" for c in tree["kids"]),
    encoding="utf-8",
)
print("tree bytes", len(TREE_JSON.encode("utf-8")))
