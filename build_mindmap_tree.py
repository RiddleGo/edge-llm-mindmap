# -*- coding: utf-8 -*-
"""Build mindmap tree from 端侧模型部署.md — thick tutorial prose into leaves."""
from __future__ import annotations

import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent
md = next(p for p in root.iterdir() if p.name == "端侧模型部署.md")
text = md.read_text(encoding="utf-8")
text = "".join(p if i % 2 == 0 else "" for i, p in enumerate(text.split("```")))


def short(s: str, n: int = 40) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    s = re.sub(r"[🃏↪⏱↔⏩⚠✅]", "", s).strip()
    s = s.replace("**", "")
    return s if len(s) <= n else s[: n - 1] + "…"


def plain(s: str) -> str:
    s = (s or "").replace("**", "").strip()
    s = re.sub(r"[ \t]+", " ", s)
    return s


def clip(s: str, n: int) -> str:
    s = plain(s)
    return s if len(s) <= n else s[: n - 1] + "…"


CIRCLE = "〇①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯"
TOP_RE = re.compile(rf"^#{{1,2}}\s+([{CIRCLE}])(?!-)\s*(.*)$")
TERM_RE = re.compile(r"^- \*\*(.+?)\*\*\s*[—–:：]\s*(.+)$")
BOLD_RE = re.compile(r"^\*\*(.+?)\*\*\s*[—–:：]\s*(.+)$")

L2_D_MAX = 3200
L3_D_MAX = 1800
L3_T_MAX = 40
L3_CAP = 80  # ⑬/⑮ 同节 ### 很多；过低会静默丢叶

tree = {
    "id": "root",
    "t": "端侧大模型部署",
    "d": "按章依次讲：〇→①→…→⑯。导出 → 变轻 → 转换 Runtime → 量稳验收 → 交付。点开看「是什么 / 作用」。",
    "kids": [],
}
cur1 = cur2 = None
ext_mark = False
l2_from_h2 = False
para_buf: list[str] = []
open_leaf: dict | None = None


def close_leaf() -> None:
    global open_leaf
    open_leaf = None


def new_l1(title: str) -> None:
    global cur1, cur2, ext_mark, l2_from_h2, para_buf
    flush_section()
    close_leaf()
    cur1 = {"id": f"c{len(tree['kids'])+1}", "t": short(title, 40), "d": "", "kids": []}
    tree["kids"].append(cur1)
    cur2 = None
    ext_mark = title.startswith(("⑬", "⑭", "⑮", "⑯"))
    l2_from_h2 = False
    para_buf = []


def new_l2(title: str, from_h2: bool = False) -> None:
    global cur2, l2_from_h2, para_buf
    flush_section()
    close_leaf()
    if not cur1:
        return
    cur2 = {
        "id": f"{cur1['id']}-{len(cur1['kids'])+1}",
        "t": short(title, 48),
        "d": "",
        "kids": [],
    }
    cur1["kids"].append(cur2)
    l2_from_h2 = from_h2
    para_buf = []


def add_l3(title: str, desc: str = "") -> dict | None:
    global open_leaf
    if not cur2:
        return None
    if len(cur2["kids"]) >= L3_CAP:
        return None
    t = short(title, L3_T_MAX)
    d = clip(desc, L3_D_MAX) if desc else ""
    for k in cur2["kids"]:
        if k["t"] == t:
            if len(d) > len(k.get("d") or ""):
                k["d"] = d
            open_leaf = k
            return k
    node = {
        "id": f"{cur2['id']}-{len(cur2['kids'])+1}",
        "t": t,
        "d": d,
        "kids": [],
        "_from_h3": False,
    }
    cur2["kids"].append(node)
    open_leaf = node
    return node


def append_prose(line: str) -> None:
    """Attach prose to the open leaf when present; else buffer for the section."""
    global open_leaf
    p = plain(line)
    if not p:
        return
    if open_leaf is not None:
        cur = open_leaf.get("d") or ""
        merged = (cur + "\n\n" + p).strip() if cur else p
        open_leaf["d"] = clip(merged, L3_D_MAX)
        return
    para_buf.append(p)


def flush_section() -> None:
    global para_buf
    if not cur2:
        para_buf = []
        return
    paras = [plain(p) for p in para_buf if plain(p)]
    para_buf = []
    if not paras:
        return
    body = "\n\n".join(paras)
    body = clip(body, L2_D_MAX)
    if len(body) > len(cur2.get("d") or ""):
        cur2["d"] = body
    if cur2["kids"]:
        # If latest leaf is still empty/short, pour unused section paras into it
        leaf = cur2["kids"][-1]
        if len(leaf.get("d") or "") < 40:
            leaf["d"] = clip((leaf.get("d") or "") + ("\n\n" if leaf.get("d") else "") + body, L3_D_MAX)
        return
    for p in paras:
        if len(p) < 12:
            continue
        title = re.split(r"[。；\n]", p, maxsplit=1)[0].strip()
        add_l3(title or p[:24], p)
    if not cur2["kids"]:
        add_l3(cur2["t"], cur2.get("d") or cur2["t"])


for raw in text.splitlines():
    line = raw.rstrip()
    tm = TOP_RE.match(line)
    if tm:
        new_l1((tm.group(1) + " " + tm.group(2)).strip())
        continue
    if re.match(r"^##\s+", line) and cur1:
        new_l2(line[3:].strip(), from_h2=True)
        continue
    if re.match(r"^###\s+", line) and cur1:
        title = line[4:].strip()
        if ext_mark and l2_from_h2 and cur2:
            flush_section()
            node = add_l3(title, "")
            if node is not None:
                node["_from_h3"] = True
        else:
            new_l2(title, from_h2=False)
        continue
    if not cur1:
        continue
    if not cur2:
        if line and not line.startswith(("#", "|", ">", "-", "*")) and not cur1["d"]:
            cur1["d"] = short(line, 240)
        continue

    # Under a ### leaf: keep bold/term as section meat, do not spawn sibling leaves
    # that later get merged away and erase the ### title (BitNet / Runbook / OTA…).
    term = TERM_RE.match(line)
    if term:
        if open_leaf is not None and open_leaf.get("_from_h3"):
            append_prose(f"{term.group(1)} — {term.group(2)}")
            continue
        flush_section()
        add_l3(term.group(1), f"{term.group(1)} — {term.group(2)}")
        continue
    bold = BOLD_RE.match(line)
    if bold:
        if open_leaf is not None and open_leaf.get("_from_h3"):
            append_prose(f"{bold.group(1)} — {bold.group(2)}")
            continue
        flush_section()
        add_l3(bold.group(1), f"{bold.group(1)} — {bold.group(2)}")
        continue
    if line.startswith("- ") or line.startswith("* "):
        body = line[2:].strip()
        body = re.sub(r"^\*\*(.+?)\*\*\s*", r"\1：", body)
        append_prose(body)
        continue
    if line.startswith(">"):
        append_prose(line.lstrip("> ").strip())
        continue
    if line.startswith("|"):
        # keep non-separator table rows as compact prose
        if re.match(r"^\|[\s\-:|]+\|$", line.replace(" ", "")):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        cells = [plain(c) for c in cells if plain(c) and c != "---"]
        if len(cells) >= 2:
            append_prose("；".join(cells))
        continue
    if line.startswith("#"):
        continue
    if not line.strip():
        continue
    if re.match(r"^\d+[\.、]\s*", line):
        append_prose(re.sub(r"^\d+[\.、]\s*", "", line))
        continue
    append_prose(line)

flush_section()
close_leaf()


BOILER = (
    "管端侧链路里这一段",
    "别把目录当正文",
    "落在「",
    "见原文档对应小节",
    "先弄清它解决哪类问题",
    "先立章目标，再进主题",
    "给学习路径一个章节锚点",
)


def thicken(tree: dict) -> None:
    for c1 in tree.get("kids") or []:
        for c2 in c1.get("kids") or []:
            parent = c2.get("d") or ""
            paras = [p.strip() for p in parent.split("\n\n") if p.strip()]
            kids = c2.get("kids") or []
            for leaf in kids:
                d = leaf.get("d") or ""
                bare = re.sub(r"^\d+(?:\.\d+)*\s*·\s*", "", leaf.get("t") or "")
                thin = len(d) < 60 or d.strip() == bare or any(b in d for b in BOILER)
                if not thin:
                    continue
                keys = [w for w in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", bare) if len(w) >= 2][:6]
                hit = ""
                for p in paras:
                    if keys and sum(1 for k in keys if k in p) >= max(1, min(2, len(keys) // 2 or 1)):
                        hit = p
                        break
                if not hit and len(kids) == 1 and parent:
                    hit = parent
                if not hit:
                    for p in paras:
                        if len(p) >= 40:
                            hit = p
                            break
                if hit:
                    if d and len(d) >= 20 and d not in hit and not any(b in d for b in BOILER):
                        leaf["d"] = clip(d + "\n\n" + hit, L3_D_MAX)
                    else:
                        leaf["d"] = clip(hit, L3_D_MAX)
                elif not d or any(b in d for b in BOILER):
                    leaf["d"] = bare + "。见本节说明。"


for c in tree["kids"]:
    c["kids"] = [s for s in c["kids"] if s["t"]]
    for s in c["kids"]:
        if not s["kids"]:
            s["kids"].append(
                {
                    "id": s["id"] + "-n",
                    "t": s["t"],
                    "d": s.get("d") or "见原文档对应小节",
                    "kids": [],
                }
            )


def renumber_teaching_order(tree: dict) -> dict:
    circle = re.compile(r"^(?:〇|①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|⑪|⑫|⑬|⑭|⑮|⑯)(?:-?\d+)?\s*[·.\s、]*\s*")
    num = re.compile(r"^(?:\d+(?:\.\d+){0,3})\s*[·.\s、\-–—]+\s*")

    def strip_old(title: str) -> str:
        t = title.strip()
        t = circle.sub("", t)
        t = num.sub("", t)
        return t.strip(" ·.-–—") or title.strip()

    for i, c1 in enumerate(tree.get("kids") or [], 1):
        c1["t"] = f"{i} · {strip_old(c1.get('t') or '')}"
        for j, c2 in enumerate(c1.get("kids") or [], 1):
            c2["t"] = f"{i}.{j} · {strip_old(c2.get('t') or '')}"
            for k, c3 in enumerate(c2.get("kids") or [], 1):
                c3["t"] = f"{i}.{j}.{k} · {strip_old(c3.get('t') or '')}"
    tree["d"] = "按章依次讲：〇→①→…→⑯。点开看「是什么 / 作用」。主题层补一句这段在链路里的位置。"
    return tree


thicken(tree)
tree = renumber_teaching_order(tree)
TREE_JSON = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
(root / "mindmap-tree.json").write_text(TREE_JSON, encoding="utf-8")

leaves = [c3 for c1 in tree["kids"] for c2 in c1.get("kids") or [] for c3 in c2.get("kids") or []]
lens = sorted(len(x.get("d") or "") for x in leaves)
thin = sum(1 for n in lens if n < 60)
boiler = sum(1 for x in leaves if any(b in (x.get("d") or "") for b in BOILER))
total = sum(len(x.get("d") or "") for x in leaves)
(root / "_tree_stats.txt").write_text(
    f"L1={len(tree['kids'])} L2={sum(len(c['kids']) for c in tree['kids'])} L3={len(leaves)}\n"
    f"L3_d_p50={lens[len(lens)//2] if lens else 0} thin<60={thin} boiler={boiler} leaf_d_chars={total}\n"
    + "\n".join(
        f"{c['t']} L2={len(c['kids'])} L3={sum(len(s['kids']) for s in c['kids'])}"
        for c in tree["kids"]
    ),
    encoding="utf-8",
)
print("tree bytes", len(TREE_JSON.encode("utf-8")))
print(f"L3={len(leaves)} p50={lens[len(lens)//2] if lens else 0} thin<60={thin} boiler={boiler} leaf_chars={total}")
for c1 in tree["kids"][:1]:
    for c2 in c1.get("kids") or []:
        if "信任边界" in (c2.get("t") or ""):
            print("TRUST L2", len(c2.get("d") or ""), "L3", len(c2.get("kids") or []))
            for leaf in c2.get("kids") or []:
                print(" ", len(leaf.get("d") or ""), leaf["t"][:36])
