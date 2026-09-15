# -*- coding: utf-8 -*-
"""Renumber mindmap nodes by teaching order; inject HTML."""
from __future__ import annotations

import json
import re
import runpy
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\推理VS训练")
HTML = ROOT / "端侧部署思维导图.html"
TPL = ROOT / "_mindmap_template.html"
TREE_JSON = ROOT / "mindmap-tree.json"
BUILDER = ROOT / "build_mindmap_tree.py"

# Original chapter glyph → keep as cross-ref tag after teaching index
CIRCLE_RE = re.compile(
    r"^(?:〇|①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|⑪|⑫|⑬|⑭|⑮|⑯)"
    r"(?:-?\d+)?\s*[·.\s、]*\s*"
)
NUM_PREFIX_RE = re.compile(
    r"^(?:\d+(?:\.\d+){0,3}|[一二三四五六七八九十]+)\s*[·.\s、\-–—]+\s*"
)


def strip_old_number(title: str) -> str:
    t = title.strip()
    t = CIRCLE_RE.sub("", t)
    t = NUM_PREFIX_RE.sub("", t)
    # also strip "附录 · " staying as content word — keep it
    return t.strip(" ·.-–—") or title.strip()


def renumber(tree: dict) -> dict:
    for i, c1 in enumerate(tree.get("kids") or [], 1):
        raw = c1.get("t") or ""
        body = strip_old_number(raw)
        # keep original circle glyph as soft tag if present
        m = re.match(r"^(〇|①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|⑪|⑫|⑬|⑭|⑮|⑯)", raw.strip())
        tag = f"（原{m.group(1)}）" if m else ""
        # appendices: mark 附
        if "附录" in raw:
            c1["t"] = f"{i} · 附 · {body}"
        else:
            c1["t"] = f"{i} · {body}{tag}" if tag and m.group(1) not in body else f"{i} · {body}"
        c1["t"] = re.sub(r"（原.+?）{2,}", lambda x: x.group(0)[:x.group(0).find("）") + 1], c1["t"])
        # cleaner: if body already starts with same meaning, just use i · body
        c1["t"] = f"{i} · {body}"

        for j, c2 in enumerate(c1.get("kids") or [], 1):
            b2 = strip_old_number(c2.get("t") or "")
            # strip leftover ⑬-9 style already handled by CIRCLE_RE
            c2["t"] = f"{i}.{j} · {b2}"
            for k, c3 in enumerate(c2.get("kids") or [], 1):
                b3 = strip_old_number(c3.get("t") or "")
                # avoid duplicating parent title as leaf
                if b3 == b2:
                    c3["t"] = f"{i}.{j}.{k} · {b3}"
                else:
                    c3["t"] = f"{i}.{j}.{k} · {b3}"
    return tree


def inject(path: Path, payload: str) -> None:
    """Brace-aware replace — regex .*? truncates nested TREE objects."""
    html = path.read_text(encoding="utf-8")
    start = html.find("const TREE = ")
    if start < 0:
        raise SystemExit(f"inject failed for {path.name}: const TREE not found")
    eq = html.find("=", start)
    i = eq + 1
    while i < len(html) and html[i] in " \n\r\t":
        i += 1
    if i >= len(html) or html[i] != "{":
        raise SystemExit(f"inject failed for {path.name}: expected {{")
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
    new_html = html[:start] + "const TREE = " + payload + ";" + html[k:]
    new_html = new_html.replace("点击展开 ①–⑯", "按 1→2→3… 序号展开")
    new_html = new_html.replace("点击展开 〇→⑫→②…→⑮", "按序号 1→2→3… 展开（并排先看小数点前的章序）")
    i2 = new_html.find("const TREE = ") + len("const TREE = ")
    while new_html[i2] in " \n\r\t":
        i2 += 1
    json.JSONDecoder().raw_decode(new_html, i2)
    path.write_text(new_html, encoding="utf-8")
    print("injected", path.name, path.stat().st_size)


def main() -> None:
    if BUILDER.exists():
        runpy.run_path(str(BUILDER), run_name="__main__")

    tree = json.loads(TREE_JSON.read_text(encoding="utf-8"))
    print("before L1:")
    for c in tree["kids"][:6]:
        print(" ", c["t"])

    tree = renumber(tree)
    # update root description
    tree["d"] = (
        "讲课序号 1→N。章=1 · …；主题=1.1；术语=1.1.1。"
        "并排时先比章序，再比小数点后主题序、术语序。"
    )

    payload = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
    TREE_JSON.write_text(payload, encoding="utf-8")
    (ROOT / "_tree_stats.txt").write_text(
        f"L1={len(tree['kids'])} "
        f"L2={sum(len(c.get('kids') or []) for c in tree['kids'])} "
        f"L3={sum(len(s.get('kids') or []) for c in tree['kids'] for s in (c.get('kids') or []))}\n"
        + "\n".join(
            f"{c['t']} | L2={len(c.get('kids') or [])}"
            for c in tree["kids"]
        ),
        encoding="utf-8",
    )

    print("after L1:")
    for c in tree["kids"]:
        print(" ", c["t"])
        for s in (c.get("kids") or [])[:2]:
            print("   ", s["t"])
            for leaf in (s.get("kids") or [])[:2]:
                print("     ", leaf["t"])

    inject(HTML, payload)
    if TPL.exists():
        tpl = TPL.read_text(encoding="utf-8")
        if "const TREE" in tpl and "{" in tpl[tpl.find("const TREE") : tpl.find("const TREE") + 40]:
            try:
                inject(TPL, payload)
            except SystemExit as e:
                print("template inject skipped:", e)
        elif "__TREE__" in tpl:
            TPL.write_text(tpl.replace("__TREE__", payload), encoding="utf-8")
            print("template placeholder filled")

    # also patch builder to renumber on every rebuild
    if BUILDER.exists():
        src = BUILDER.read_text(encoding="utf-8")
        if "def renumber_teaching_order" not in src:
            hook = '''
def renumber_teaching_order(tree):
    import re
    circle = re.compile(r"^(?:〇|①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|⑪|⑫|⑬|⑭|⑮|⑯)(?:-?\\d+)?\\s*[·.\\s、]*\\s*")
    num = re.compile(r"^(?:\\d+(?:\\.\\d+){0,3})\\s*[·.\\s、\\\\-–—]+\\s*")
    def strip_old(title):
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
    tree["d"] = "讲课序号 1→N。章=1；主题=1.1；术语=1.1.1。并排先看序号。"
    return tree

'''
            if "TREE_JSON = json.dumps" in src:
                src = src.replace(
                    "TREE_JSON = json.dumps",
                    hook + "tree = renumber_teaching_order(tree)\nTREE_JSON = json.dumps",
                    1,
                )
                BUILDER.write_text(src, encoding="utf-8")
                print("builder hooked")
            else:
                print("builder dump marker missing, skip hook")

    print("OK")


if __name__ == "__main__":
    main()
