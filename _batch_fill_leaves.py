# -*- coding: utf-8 -*-
"""Batch-fill TREE_MAIN leaves to the 1.1 showcase standard.

Standard:
- multi-paragraph lecture body in d (\\n\\n), typically 220–900 chars
- useful w (起什么作用)
- k=1/2 on real teaching pivots
- **bold** on 拒收 / 硬口径句
Source of truth: 端侧模型部署.md section prose.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
MD = ROOT / "端侧模型部署.md"
TREE = ROOT / "mindmap-tree.json"

TARGET_MIN = 220
TARGET_SOFT = 420
CAP = 1600
NUM = re.compile(r"^\d+(?:\.\d+)*\s*[·.\s、\-–—]+\s*")
CIRCLE = re.compile(r"^[〇①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯](?:-\d+)?\s*")

CORE_KEYS = (
    "信任边界", "访存墙", "现场拒收", "Prefill", "Decode", "三个词先对齐",
    "端（on-device）", "量化基础", "KV", "交付门禁", "能加载", "能量化",
)
FOCUS_KEYS = (
    "近边", "云", "校准", "PTQ", "QAT", "投机", "温区", "OTA", "门禁",
    "ONNX", "Runtime", "算子", "指纹", "回落", "TTFT", "Paged",
)


def strip_title(t: str) -> str:
    t = (t or "").strip()
    t = NUM.sub("", t)
    t = CIRCLE.sub("", t)
    return t.strip(" ·.-–—")


def plain_line(s: str) -> str:
    s = (s or "").replace("\u3000", " ")
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s


def md_to_paras(blob: str) -> list[str]:
    """Turn a markdown section into readable paragraphs."""
    lines: list[str] = []
    for raw in blob.splitlines():
        line = raw.rstrip()
        if not line.strip():
            lines.append("")
            continue
        if line.startswith("```"):
            continue
        if re.match(r"^\|[\s\-:|]+\|$", line.replace(" ", "")):
            continue
        if line.startswith("|"):
            cells = [plain_line(c.replace("**", "")) for c in line.strip("|").split("|")]
            cells = [c for c in cells if c and c != "---"]
            if len(cells) >= 2:
                lines.append("；".join(cells))
            continue
        if line.startswith(">"):
            line = line.lstrip("> ").strip()
        if line.startswith("#"):
            continue
        # keep bold markers for later emphasis; strip list bullets
        if line.startswith(("- ", "* ")):
            line = line[2:].strip()
            line = re.sub(r"^\*\*(.+?)\*\*\s*[—–:：]\s*", r"**\1** — ", line)
        if re.match(r"^\d+[\.、]\s*", line):
            line = re.sub(r"^\d+[\.、]\s*", "", line)
        lines.append(plain_line(line))

    # join consecutive non-empty into paras; blank line breaks
    paras: list[str] = []
    buf: list[str] = []
    for line in lines:
        if not line:
            if buf:
                paras.append(" ".join(buf))
                buf = []
            continue
        buf.append(line)
    if buf:
        paras.append(" ".join(buf))

    out: list[str] = []
    for p in paras:
        p = re.sub(r"\s+", " ", p).strip()
        if len(p) < 18:
            continue
        # drop pure checkbox noise
        if p.startswith("[ ]") or p.startswith("- [ ]"):
            continue
        out.append(p)
    return out


def parse_md_sections(text: str) -> dict[str, list[str]]:
    text = "".join(p if i % 2 == 0 else "" for i, p in enumerate(text.split("```")))
    sections: dict[str, list[str]] = {}
    cur: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal cur, buf
        if cur:
            sections[cur] = md_to_paras("\n".join(buf))
        cur = None
        buf = []

    for raw in text.splitlines():
        if re.match(r"^###\s+", raw):
            flush()
            cur = raw[4:].strip()
            buf = []
            continue
        if re.match(r"^##\s+", raw):
            flush()
            # also index ## as section (⑬-x hubs)
            cur = raw[3:].strip()
            buf = []
            continue
        if cur is not None:
            buf.append(raw)
    flush()
    return sections


def score_para(para: str, keys: list[str]) -> int:
    s = 0
    low = para.lower()
    for k in keys:
        if not k:
            continue
        if k.lower() in low or k in para:
            s += 2 if len(k) >= 2 else 1
    if "拒收" in para:
        s += 2
    if "验收" in para:
        s += 1
    return s


def pick_paras(paras: list[str], keys: list[str], existing: str) -> list[str]:
    if not paras:
        return []
    ranked = sorted(
        ((score_para(p, keys), i, p) for i, p in enumerate(paras)),
        key=lambda x: (-x[0], x[1]),
    )
    chosen: list[str] = []
    used: set[int] = set()
    # first: high-score hits
    for sc, i, p in ranked:
        if sc < 1:
            break
        if i in used:
            continue
        if existing and p[:40] in existing:
            continue
        chosen.append(p)
        used.add(i)
        if sum(len(x) for x in chosen) >= TARGET_SOFT:
            break
        if len(chosen) >= 4:
            break
    # pad with sequential meat if still thin
    if sum(len(x) for x in chosen) < TARGET_MIN:
        for i, p in enumerate(paras):
            if i in used or len(p) < 40:
                continue
            if existing and p[:40] in existing:
                continue
            chosen.append(p)
            used.add(i)
            if sum(len(x) for x in chosen) >= TARGET_SOFT or len(chosen) >= 5:
                break
    return chosen


def clip(s: str, n: int = CAP) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    cut = s[: n - 1]
    for sep in ("。", "；", "\n\n", "，"):
        j = cut.rfind(sep)
        if j >= int(n * 0.55):
            return cut[: j + (0 if sep == "\n\n" else 1)] + "…"
    return cut + "…"


def emphasize(s: str) -> str:
    """Add light ** markers without doubling."""
    if "拒收：" in s and "**拒收：**" not in s:
        s = s.replace("拒收：", "**拒收：**", 1)
    if "拒收话术" in s and "**拒收话术**" not in s:
        s = s.replace("拒收话术", "**拒收话术**", 1)
    return s


def find_section(sections: dict[str, list[str]], bare: str, parent_bare: str) -> list[str]:
    # exact / containment
    for title, paras in sections.items():
        if bare and (bare == title or bare in title or title in bare):
            return paras
    for title, paras in sections.items():
        if parent_bare and (parent_bare == title or parent_bare in title or title in parent_bare):
            return paras
    # token overlap
    keys = [w for w in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", bare) if len(w) >= 2][:8]
    best_t, best_sc = "", -1
    for title, paras in sections.items():
        sc = sum(1 for k in keys if k in title)
        if sc > best_sc:
            best_sc, best_t = sc, title
    if best_sc >= 1:
        return sections[best_t]
    return []


def make_w(bare: str, d: str) -> str:
    if "拒收" in d:
        return f"弄清「{bare}」是为了把验收/拒收说清楚，避免海报口径混进门禁。"
    if any(x in bare or x in d for x in ("Prefill", "Decode", "TTFT", "访存")):
        return f"「{bare}」决定测哪张表、动哪根杠杆；混阶段会把优化做反。"
    if any(x in bare for x in ("量化", "校准", "PTQ", "QAT", "INT")):
        return f"「{bare}」连着体积、带宽与掉点；端侧先问塞不塞得下、再问准不准。"
    return f"弄清「{bare}」，排障和选型时才知道该动哪一环。"


def mark_k(bare: str, d: str) -> int:
    for k in CORE_KEYS:
        if k in bare or (len(k) >= 3 and k in (d or "")[:80]):
            return 2
    for k in FOCUS_KEYS:
        if k.lower() in bare.lower() or k in bare:
            return 1
    if "拒收" in (d or ""):
        return 1
    return 0


def main() -> None:
    sections = parse_md_sections(MD.read_text(encoding="utf-8"))
    tree = json.loads(TREE.read_text(encoding="utf-8"))

    filled = 0
    kept = 0
    keyed = 0
    bolded = 0

    for c1 in tree.get("kids") or []:
        for c2 in c1.get("kids") or []:
            parent_bare = strip_title(c2.get("t") or "")
            parent_paras = find_section(sections, parent_bare, parent_bare)
            # thicken L2 hub if thin
            if len(c2.get("d") or "") < 160 and parent_paras:
                hub = pick_paras(parent_paras, [parent_bare], c2.get("d") or "")
                if hub:
                    c2["d"] = clip("\n\n".join(hub), 900)
            if not c2.get("w") or len(c2.get("w") or "") < 20:
                c2["w"] = make_w(parent_bare, c2.get("d") or "")
            pk = mark_k(parent_bare, c2.get("d") or "")
            if pk and not c2.get("k"):
                c2["k"] = pk
                keyed += 1

            for leaf in c2.get("kids") or []:
                bare = strip_title(leaf.get("t") or "")
                d = (leaf.get("d") or "").strip()
                paras_n = len([p for p in d.split("\n\n") if p.strip()]) if d else 0
                already_good = len(d) >= TARGET_SOFT and paras_n >= 2
                if already_good:
                    kept += 1
                    # still allow key/bold polish
                    if not leaf.get("k"):
                        k = mark_k(bare, d)
                        if k:
                            leaf["k"] = k
                            keyed += 1
                    new_d = emphasize(d)
                    if new_d != d:
                        leaf["d"] = new_d
                        bolded += 1
                    continue

                sec = find_section(sections, bare, parent_bare)
                keys = [w for w in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", bare) if len(w) >= 2][:8]
                if parent_bare:
                    keys.append(parent_bare[:12])
                picked = pick_paras(sec or parent_paras, keys, d)

                chunks: list[str] = []
                if d and len(d) >= 40 and not d.startswith("见原文档"):
                    # keep existing meat as first para if not boilerplate
                    if not any(b in d for b in ("管端侧链路", "别把目录当正文", "见本节说明")):
                        chunks.append(d if "\n\n" in d else d)
                for p in picked:
                    if any(p in c or c in p for c in chunks):
                        continue
                    chunks.append(p)
                    if sum(len(x) for x in chunks) >= TARGET_SOFT and len(chunks) >= 2:
                        break
                    if len(chunks) >= 5:
                        break

                if not chunks and (sec or parent_paras):
                    pool = sec or parent_paras
                    chunks = pool[:3]

                if chunks:
                    merged = emphasize(clip("\n\n".join(chunks), CAP))
                    if len(merged) > len(d) + 30 or paras_n < 2:
                        leaf["d"] = merged
                        filled += 1
                    else:
                        leaf["d"] = emphasize(d)
                elif d:
                    leaf["d"] = emphasize(d)

                if not leaf.get("w") or len(leaf.get("w") or "") < 18:
                    leaf["w"] = make_w(bare, leaf.get("d") or "")
                if not leaf.get("k"):
                    k = mark_k(bare, leaf.get("d") or "")
                    if k:
                        leaf["k"] = k
                        keyed += 1
                if "**" in (leaf.get("d") or ""):
                    bolded += 1

    payload = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
    TREE.write_text(payload, encoding="utf-8")

    import _enrich_content_v2 as e

    for html in e.HTMLS:
        if html.exists():
            e.inject(html, payload)

    leaves = [
        c3
        for c1 in tree["kids"]
        for c2 in c1.get("kids") or []
        for c3 in c2.get("kids") or []
    ]
    lens = sorted(len(x.get("d") or "") for x in leaves)
    thin = sum(1 for n in lens if n < 120)
    multi = sum(1 for x in leaves if (x.get("d") or "").count("\n\n") >= 1)
    keyed_n = sum(1 for x in leaves if x.get("k"))
    print(
        f"filled={filled} kept_good={kept} keyed_new≈{keyed} bold_touch={bolded}\n"
        f"L3={len(leaves)} p50={lens[len(lens)//2]} p90={lens[int(len(lens)*0.9)]} "
        f"mean={int(sum(lens)/len(leaves))} thin<120={thin}({100*thin/len(leaves):.1f}%) "
        f"multi-para={multi} keyed={keyed_n} chars={sum(lens)}"
    )


if __name__ == "__main__":
    main()
