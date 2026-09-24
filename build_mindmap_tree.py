# -*- coding: utf-8 -*-
"""Build mindmap tree from 端侧模型部署.md — faithful section prose, no rewrite."""
from __future__ import annotations

import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent
md = next(p for p in root.iterdir() if p.name == "端侧模型部署.md")
raw_text = md.read_text(encoding="utf-8")


def strip_fences(src: str) -> str:
    """Keep fenced body as plain lines (drop language tag only)."""
    parts = src.split("```")
    out: list[str] = []
    for i, p in enumerate(parts):
        if i % 2 == 0:
            out.append(p)
            continue
        lines = p.splitlines()
        if lines and re.match(r"^[A-Za-z0-9_+\-]*\s*$", lines[0]):
            lines = lines[1:]
        out.append("\n".join(lines))
    return "".join(out)


text = strip_fences(raw_text)

CN_TOP = re.compile(r"^#{1,2}\s+([一二三四五六七八九十]{1,3})、\s*(.+)$")
CIRCLE_TOP = re.compile(r"^#{1,2}\s+([〇①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯])(?!-)\s*(.*)$")
TERM = re.compile(r"^- \*\*(.+?)\*\*\s*[—–:：]\s*(.+)$")
BOLD = re.compile(r"^\*\*(.+?)\*\*\s*[—–:：]\s*(.+)$")
BOLD_LEAD = re.compile(r"^\*\*([①-⑳]?\s*.+?)\*\*\s+(.+)$")
CIRCLE_ITEM = re.compile(r"^[①-⑳]")

L2_D_MAX = 12000
L1_D_MAX = 12000
L3_D_MAX = 6000
L3_T_MAX = 48
L3_CAP = 100


def short(s: str, n: int = 48) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    return s if len(s) <= n else s[: n - 1] + "…"


def clip(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def normalize_para(line: str) -> str:
    """Keep markdown emphasis; lightly flatten tables/lists for the reader panel."""
    line = line.rstrip()
    if not line.strip():
        return ""
    if re.match(r"^\|[\s\-:|]+\|$", line.replace(" ", "")):
        return ""
    if line.startswith("|"):
        cells = [c.strip().replace("**", "") for c in line.strip("|").split("|")]
        cells = [c for c in cells if c and c != "---"]
        if len(cells) < 2:
            return ""
        return "；".join(cells)
    if line.startswith(">"):
        return line.lstrip("> ").strip()
    if re.match(r"^[-*]{3,}\s*$", line.strip()):
        return ""
    if line.startswith(("- ", "* ")):
        body = line[2:].strip()
        m = TERM.match(line) or re.match(r"^- \*\*(.+?)\*\*\s*(.*)$", line)
        if m and m.lastindex and m.lastindex >= 2 and m.group(2):
            return f"**{m.group(1)}** — {m.group(2).lstrip('—–:： ').strip()}"
        return body
    return line.strip()


tree = {
    "id": "root",
    "t": "端侧大模型部署",
    "d": "按岗位画像 → 能力分层 → 五层技能 → 面试考点展开。右侧讲义直接来自《端侧模型部署.md》原文。",
    "kids": [],
}
cur1 = cur2 = None
para_buf: list[str] = []
l1_buf: list[str] = []
open_leaf: dict | None = None
leaf_gap = False


def text_from_buf(buf: list[str]) -> str:
    """Blank line → paragraph gap; consecutive lines → hard line breaks."""
    paras: list[str] = []
    cur: list[str] = []
    for p in buf:
        if p == "":
            if cur:
                paras.append("\n".join(cur))
                cur = []
        else:
            cur.append(p)
    if cur:
        paras.append("\n".join(cur))
    return "\n\n".join(paras)


def flush_l1() -> None:
    global l1_buf
    if not cur1 or not l1_buf:
        l1_buf = []
        return
    body = text_from_buf(l1_buf)
    l1_buf = []
    if not body:
        return
    cur = (cur1.get("d") or "").strip()
    cur1["d"] = clip((cur + "\n\n" + body).strip() if cur else body, L1_D_MAX)


def flush_paras_into_l2() -> None:
    global para_buf
    if not cur2 or not para_buf:
        para_buf = []
        return
    body = text_from_buf(para_buf)
    para_buf = []
    if not body:
        return
    cur = cur2.get("d") or ""
    merged = (cur + "\n\n" + body).strip() if cur else body
    cur2["d"] = clip(merged, L2_D_MAX)


def close_leaf() -> None:
    global open_leaf, leaf_gap
    open_leaf = None
    leaf_gap = False


def append_open(p: str) -> None:
    """Consecutive lines break; a prior blank line starts a new paragraph."""
    global leaf_gap
    if open_leaf is None or not p:
        return
    cur = open_leaf.get("d") or ""
    sep = "\n\n" if cur and leaf_gap else ("\n" if cur else "")
    open_leaf["d"] = clip(cur + sep + p, L3_D_MAX)
    leaf_gap = False


def new_l1(title: str) -> None:
    global cur1, cur2, para_buf, l1_buf
    flush_paras_into_l2()
    flush_l1()
    close_leaf()
    cur1 = {"id": f"c{len(tree['kids']) + 1}", "t": short(title, 56), "d": "", "kids": []}
    tree["kids"].append(cur1)
    cur2 = None
    para_buf = []
    l1_buf = []


def new_l2(title: str) -> None:
    global cur2, para_buf
    flush_l1()
    flush_paras_into_l2()
    close_leaf()
    if not cur1:
        return
    cur2 = {
        "id": f"{cur1['id']}-{len(cur1['kids']) + 1}",
        "t": short(title, 56),
        "d": "",
        "kids": [],
    }
    cur1["kids"].append(cur2)
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
    node = {"id": f"{cur2['id']}-{len(cur2['kids']) + 1}", "t": t, "d": d, "kids": []}
    cur2["kids"].append(node)
    open_leaf = node
    return node


def ensure_theme_for_loose_content(line: str) -> None:
    """When a chapter has no ### yet but hits structured content, open a theme."""
    global cur2
    if cur2 or not cur1:
        return
    lead = BOLD_LEAD.match(line) or BOLD.match(line) or TERM.match(line)
    if lead and CIRCLE_ITEM.match(lead.group(1).lstrip()):
        new_l2(lead.group(1).strip("。；; "))
        return
    new_l2("要点")


for raw in text.splitlines():
    line = raw.rstrip()

    m_cn = CN_TOP.match(line)
    if m_cn:
        new_l1(f"{m_cn.group(1)}、{m_cn.group(2).strip()}")
        continue
    m_ci = CIRCLE_TOP.match(line)
    if m_ci:
        new_l1((m_ci.group(1) + " " + m_ci.group(2)).strip())
        continue

    if re.match(r"^##\s+", line) and cur1:
        # Non-numbered ## under a chapter → theme
        new_l2(line[3:].strip())
        continue

    if re.match(r"^###\s+", line) and cur1:
        new_l2(line[4:].strip())
        continue

    if not cur1:
        continue

    if not cur2:
        structured = bool(
            line.startswith(("- ", "* ", "|"))
            or TERM.match(line)
            or BOLD.match(line)
            or BOLD_LEAD.match(line)
            or CIRCLE_ITEM.match(line.lstrip("*").lstrip())
        )
        if line.startswith("#"):
            continue
        if not line.strip() or re.match(r"^[-*]{3,}\s*$", line.strip()):
            if l1_buf and l1_buf[-1] != "":
                l1_buf.append("")
            continue
        if not structured:
            p = normalize_para(line)
            if p:
                l1_buf.append(p)
            continue
        ensure_theme_for_loose_content(line)

    # term / bold leaves
    term = TERM.match(line)
    if term:
        flush_paras_into_l2()
        add_l3(term.group(1), f"**{term.group(1)}** — {term.group(2)}")
        continue
    bold = BOLD.match(line)
    if bold:
        flush_paras_into_l2()
        add_l3(bold.group(1), f"**{bold.group(1)}** — {bold.group(2)}")
        continue
    bold_lead = BOLD_LEAD.match(line)
    if bold_lead:
        title = bold_lead.group(1).strip("。；; ")
        body = bold_lead.group(2).strip()
        if CIRCLE_ITEM.match(title):
            # short circled JD bullets: theme-level only (no fake 1.1.1)
            new_l2(title)
            cur2["d"] = clip(f"**{title}** — {body}", L2_D_MAX)
            close_leaf()
            continue
        flush_paras_into_l2()
        add_l3(title, f"**{title}** — {body}")
        continue

    if line.startswith(("- ", "* ")):
        p = normalize_para(line)
        if p:
            if open_leaf is not None:
                append_open(p)
            else:
                para_buf.append(p)
        continue

    if not line.strip() or re.match(r"^[-*]{3,}\s*$", line.strip()):
        if open_leaf is not None:
            leaf_gap = True
        elif para_buf and para_buf[-1] != "":
            para_buf.append("")
        continue

    if line.startswith("#"):
        continue

    p = normalize_para(line)
    if not p:
        continue
    if open_leaf is not None:
        append_open(p)
    else:
        para_buf.append(p)

flush_paras_into_l2()
flush_l1()
close_leaf()


def bare_title(title: str) -> str:
    t = (title or "").strip()
    t = re.sub(r"^(?:\d+(?:\.\d+)*)\s*[·.\s、\-–—]+\s*", "", t)
    t = re.sub(r"^[一二三四五六七八九十]{1,3}、\s*", "", t)
    t = re.sub(r"^[〇①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯①-⑳]\s*", "", t)
    return t.strip(" ·.-–—")


def titles_alike(a: str, b: str) -> bool:
    x, y = bare_title(a), bare_title(b)
    if not x or not y:
        return False
    if x == y:
        return True
    if x in y or y in x:
        return True
    return False


def adaptive_depth(tree: dict) -> None:
    """Keep L3 only when a theme has enough distinct points; otherwise stop at theme.

    - fewer than KEEP_L3_MIN leaves → fold into L2.d（根→章→主题）
    - KEEP_L3_MIN+ leaves → keep L3（根→章→主题→知识点）
    - L1 with a lone empty「要点」wrapper → promote its kids
    """
    KEEP_L3_MIN = 99

    for c1 in tree.get("kids") or []:
        kids = c1.get("kids") or []
        # promote lone wrapper themes
        if len(kids) == 1 and bare_title(kids[0].get("t") or "") in ("要点", "本章要点"):
            wrap = kids[0]
            if wrap.get("kids"):
                c1["kids"] = wrap["kids"]
                if not (c1.get("d") or "").strip() and (wrap.get("d") or "").strip():
                    c1["d"] = wrap["d"]
            elif (wrap.get("d") or "").strip():
                c1["d"] = clip(
                    ((c1.get("d") or "") + "\n\n" + wrap["d"]).strip()
                    if c1.get("d")
                    else wrap["d"],
                    L2_D_MAX,
                )
                c1["kids"] = []
            kids = c1.get("kids") or []

        for c2 in kids:
            leaves = c2.get("kids") or []
            body = (c2.get("d") or "").strip()

            # no leaves: prose stays on theme — good (3 levels)
            if not leaves:
                continue

            # few leaves → fold into theme
            fold = False
            if len(leaves) < KEEP_L3_MIN:
                fold = True
            elif len(leaves) == 1 and titles_alike(c2.get("t") or "", leaves[0].get("t") or ""):
                fold = True

            if not fold:
                # still merge empty theme body from first leaf if theme d blank? keep as is
                continue

            chunks: list[str] = []
            if body:
                chunks.append(body)
            for leaf in leaves:
                ld = (leaf.get("d") or "").strip()
                lt = bare_title(leaf.get("t") or "")
                if not ld:
                    continue
                # avoid duplicating if leaf is just title-echo of theme
                if titles_alike(c2.get("t") or "", leaf.get("t") or "") and ld:
                    if ld not in chunks and not any(ld[:40] in c for c in chunks):
                        chunks.append(ld)
                else:
                    # keep distinct point with its title when folding multi
                    piece = ld if ld.startswith("**") or ld.startswith(lt) else f"**{lt}** — {ld}"
                    if not any(piece[:40] in c for c in chunks):
                        chunks.append(piece)
            c2["d"] = clip("\n\n".join(chunks), L2_D_MAX) if chunks else body
            c2["kids"] = []

        # drop empty L2 husks
        c1["kids"] = [
            c2
            for c2 in (c1.get("kids") or [])
            if (c2.get("t") or "").strip()
            and ((c2.get("d") or "").strip() or (c2.get("kids") or []))
        ]


adaptive_depth(tree)


def renumber(tree: dict) -> dict:
    cn = re.compile(r"^[一二三四五六七八九十]{1,3}、\s*")
    circle = re.compile(r"^[〇①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯](?:-?\d+)?\s*[·.\s、]*\s*")
    num = re.compile(r"^(?:\d+(?:\.\d+){0,3})\s*[·.\s、\-–—]+\s*")

    def strip_old(title: str) -> str:
        t = title.strip()
        t = circle.sub("", t)
        t = cn.sub("", t)
        t = num.sub("", t)
        return t.strip(" ·.-–—") or title.strip()

    for i, c1 in enumerate(tree.get("kids") or [], 1):
        c1["t"] = f"{i} · {strip_old(c1.get('t') or '')}"
        for j, c2 in enumerate(c1.get("kids") or [], 1):
            c2["t"] = f"{i}.{j} · {strip_old(c2.get('t') or '')}"
            for k, c3 in enumerate(c2.get("kids") or [], 1):
                c3["t"] = f"{i}.{j}.{k} · {strip_old(c3.get('t') or '')}"
    return tree


tree = renumber(tree)
payload = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
(root / "mindmap-tree.json").write_text(payload, encoding="utf-8")

leaves = [c3 for c1 in tree["kids"] for c2 in c1.get("kids") or [] for c3 in c2.get("kids") or []]
lens = sorted(len(x.get("d") or "") for x in leaves)
(root / "_tree_stats.txt").write_text(
    f"L1={len(tree['kids'])} L2={sum(len(c['kids']) for c in tree['kids'])} L3={len(leaves)}\n"
    f"L3_d_p50={lens[len(lens)//2] if lens else 0} leaf_d_chars={sum(lens)}\n"
    + "\n".join(
        f"{c['t']} L2={len(c['kids'])} L3={sum(len(s['kids']) for s in c['kids'])}"
        for c in tree["kids"]
    ),
    encoding="utf-8",
)
print("tree bytes", len(payload.encode("utf-8")))
print(
    f"L1={len(tree['kids'])} L2={sum(len(c['kids']) for c in tree['kids'])} "
    f"L3={len(leaves)} p50={lens[len(lens)//2] if lens else 0} chars={sum(lens)}"
)
