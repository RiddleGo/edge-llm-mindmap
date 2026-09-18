# -*- coding: utf-8 -*-
"""Build jd-gap-tree.json from JD能力缺口补全.md — keep leaf text thick."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MD = ROOT / "JD能力缺口补全.md"


def short(s: str, n: int = 80) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    s = s.replace("**", "")
    return s if len(s) <= n else s[: n - 1] + "…"


def strip_md(s: str) -> str:
    s = re.sub(r"[*_`]+", "", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def split_sents(blob: str) -> list[str]:
    parts = re.split(r"(?<=[。！？；])", blob)
    return [p.strip() for p in parts if len(p.strip()) >= 18]


def thicken_from_section_prose(tree: dict) -> None:
    """Attach unused section sentences to thin L3 leaves; fill empty L2.d."""
    target = 160
    cap = 520

    def pick(sents: list[str], used: set[int], keys: list[str], hint: str) -> int:
        best_i, best_score = -1, 0
        for i, s in enumerate(sents):
            if i in used or len(s) < 28:
                continue
            score = sum(1 for k in keys if k.lower() in s.lower())
            if hint and hint[:10] in s:
                score += 2
            if score > best_score:
                best_score, best_i = score, i
        if best_i >= 0 and best_score >= 1:
            return best_i
        for i, s in enumerate(sents):
            if i not in used and len(s) >= 40:
                return i
        for i, s in enumerate(sents):
            if i not in used and len(s) >= 28:
                return i
        return -1

    for c1 in tree["kids"]:
        for c2 in c1.get("kids") or []:
            paras = c2.pop("_paras", []) or []
            blob = " ".join(strip_md(p) for p in paras)
            sents = split_sents(blob)
            if not c2.get("d"):
                meat = [s for s in sents if len(s) > 40 and not s.startswith("拒收")]
                if meat:
                    c2["d"] = short(meat[0], 280)
            elif len(c2.get("d") or "") < 80 and sents:
                extra0 = sents[0]
                if extra0 not in c2["d"]:
                    c2["d"] = short(c2["d"].rstrip("。；; ") + "。" + extra0, 280)
            used: set[int] = set()
            for leaf in c2.get("kids") or []:
                d = (leaf.get("d") or "").strip()
                bare = re.sub(r"^\d+(?:\.\d+)*\s*·\s*", "", leaf.get("t") or "")
                keys = [w for w in re.split(r"[\s/→≠=+\-—–:：·]+", bare) if len(w) >= 2][:8]
                chunks: list[str] = []
                if d and d != bare:
                    chunks.append(d)
                while sum(len(x) for x in chunks) < target:
                    idx = pick(sents, used, keys, d)
                    if idx < 0:
                        break
                    used.add(idx)
                    extra = sents[idx]
                    if any(extra in c or c in extra for c in chunks):
                        continue
                    chunks.append(extra)
                    if len(chunks) >= 4:
                        break
                if not chunks:
                    continue
                merged = chunks[0]
                for extra in chunks[1:]:
                    merged = merged.rstrip("。；; ") + "。" + extra
                leaf["d"] = short(merged, cap)
            # last resort: pad leftover thin leaves with L2.d (same chapter, not invented)
            hub = (c2.get("d") or "").strip()
            for leaf in c2.get("kids") or []:
                d = (leaf.get("d") or "").strip()
                if len(d) >= 40 or not hub:
                    continue
                if d and d in hub:
                    leaf["d"] = short(hub, 220)
                else:
                    leaf["d"] = short((d.rstrip("。；; ") + "。" + hub) if d else hub, 220)


def main() -> None:
    text = MD.read_text(encoding="utf-8")
    text = "".join(p if i % 2 == 0 else "" for i, p in enumerate(text.split("```")))
    tree = {
        "id": "root",
        "t": "JD 能力缺口补全",
        "d": "与端侧主线并列。补指令流水、DSA/内存层次、DeepSeek MLA、框架源码向、TGI、Glow、RISC-V、集合通信、云 Serving。投递缺哪块补哪块；数字写条件。",
        "kids": [],
        "w": "投递/面试缺哪块补哪块，不替代端侧连载。",
        "b": "",
        "k": 0,
    }
    cur1 = cur2 = None
    term_re = re.compile(r"^- \*\*(.+?)\*\*\s*[—–:：]\s*(.+)$")
    h4_re = re.compile(r"^####\s+(.+)$")

    def new_l1(title: str) -> None:
        nonlocal cur1, cur2
        cur1 = {
            "id": f"j{len(tree['kids'])+1}",
            "t": title,
            "d": "",
            "kids": [],
            "w": "",
            "b": "",
            "k": 0,
        }
        tree["kids"].append(cur1)
        cur2 = None

    def new_l2(title: str) -> None:
        nonlocal cur2
        if not cur1:
            return
        cur2 = {
            "id": f"{cur1['id']}-{len(cur1['kids'])+1}",
            "t": title,
            "d": "",
            "kids": [],
            "w": "",
            "b": "",
            "k": 0,
            "_paras": [],
        }
        cur1["kids"].append(cur2)

    def add_l3(title: str, desc: str = "") -> None:
        if not cur2:
            return
        t = short(title, 36)
        # merge if same title already present
        for k in cur2["kids"]:
            if k["t"] == t or short(k["t"].split(" · ")[-1], 36) == t:
                if desc and len(desc) > len(k.get("d") or ""):
                    k["d"] = short(desc, 520)
                return
        cur2["kids"].append(
            {
                "id": f"{cur2['id']}-{len(cur2['kids'])+1}",
                "t": t,
                "d": short(desc, 520) if desc else short(title, 200),
                "kids": [],
                "w": short(f"弄清「{t}」，对标 JD 时才知道缺口在哪。", 72),
                "b": "",
                "k": 0,
            }
        )

    buf_paras: list[str] = []

    def flush_paras() -> None:
        nonlocal buf_paras
        if not cur2 or not buf_paras:
            buf_paras = []
            return
        # first meaty paragraph → L2.d only (do not invent noisy leaves)
        if cur2 is not None:
            cur2.setdefault("_paras", []).extend(buf_paras)
        meat = [
            strip_md(p)
            for p in buf_paras
            if len(strip_md(p)) > 40
            and not re.match(r"^\d+[\.、]\s*", strip_md(p))
            and not strip_md(p).startswith("拒收")
        ]
        if meat and not cur2.get("d"):
            cur2["d"] = short(meat[0], 220)
        buf_paras = []

    skip_l1 = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if re.match(r"^##\s+", line):
            flush_paras()
            title = line[3:].strip()
            # meta / reference chapters stay in the md, not as empty mind-map hubs
            if re.search(r"出处|速查|附录|changelog", title, re.I):
                skip_l1 = True
                cur1 = cur2 = None
                continue
            skip_l1 = False
            new_l1(title)
            continue
        if skip_l1:
            continue
        if re.match(r"^###\s+", line) and cur1:
            flush_paras()
            new_l2(line[4:].strip())
            continue
        hm = h4_re.match(line)
        if hm and cur2:
            flush_paras()
            add_l3(hm.group(1), "")
            continue
        if not cur1:
            continue
        if not cur2:
            if line and not line.startswith(("#", "|", ">", "-", "*")) and not cur1["d"]:
                cur1["d"] = short(line, 200)
            continue
        tm = term_re.match(line)
        if tm:
            flush_paras()
            add_l3(tm.group(1), tm.group(2))
            continue
        # bullet lists stay in md; **bold prose** is section meat, keep it
        if line.startswith("- ") or line.startswith("* "):
            continue
        if line.startswith("|") or not line.strip():
            continue
        if line.startswith(">"):
            line = line.lstrip("> ").strip()
            if not line:
                continue
        if line.startswith("#"):
            continue
        # numbered items: keep as L2 meat, do not spawn extra leaves
        buf_paras.append(line)
        cleaned = strip_md(line)
        if not cur2.get("d") and len(cleaned) > 40:
            cur2["d"] = short(cleaned, 280)

    flush_paras()
    thicken_from_section_prose(tree)

    # teaching numbers
    for i, c1 in enumerate(tree["kids"], 1):
        c1["t"] = re.sub(r"^[①-⑳]\s*", "", c1["t"])
        c1["t"] = f"{i} · {c1['t']}"
        if not c1.get("w"):
            c1["w"] = "给 JD 缺口一个章节锚点。"
        if not c1.get("b"):
            prev = tree["kids"][i - 2]["t"] if i > 1 else ""
            nxt = tree["kids"][i]["t"] if i < len(tree["kids"]) else ""
            c1["b"] = short(
                f"主线之外的补全章。{('接 '+prev+'。') if prev else ''}"
                f"{('下一步 '+nxt+'。') if nxt else '补完后回端侧主线验收。'}",
                140,
            )
        for j, c2 in enumerate(c1["kids"], 1):
            c2["t"] = f"{i}.{j} · {c2['t']}"
            if not c2.get("w"):
                c2["w"] = short(f"服务「{c1['t']}」落地。", 56)
            if not c2.get("b"):
                themes = [x["t"] for x in c2["kids"][:5]]
                c2["b"] = short(
                    f"补主线未写透的一块。下含：{'、'.join(t.split(' · ')[-1] for t in themes) or '子点'}。",
                    160,
                )
            if not c2["kids"]:
                c2["kids"].append(
                    {
                        "id": f"{c2['id']}-n",
                        "t": f"{i}.{j}.1 · {c2['t'].split(' · ', 1)[-1]}",
                        "d": c2.get("d") or "见 JD能力缺口补全.md 对应节。",
                        "kids": [],
                        "w": c2.get("w") or "",
                        "b": "",
                        "k": 0,
                    }
                )
            else:
                for k, leaf in enumerate(c2["kids"], 1):
                    bare = re.sub(r"^\d+(?:\.\d+)*\s*·\s*", "", leaf["t"])
                    leaf["t"] = f"{i}.{j}.{k} · {bare}"
                    if not leaf.get("d"):
                        leaf["d"] = short(bare, 160)

    out = ROOT / "jd-gap-tree.json"
    out.write_text(json.dumps(tree, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    stats = (
        f"L1={len(tree['kids'])} "
        f"L2={sum(len(c['kids']) for c in tree['kids'])} "
        f"L3={sum(len(s['kids']) for c in tree['kids'] for s in c['kids'])}\n"
        + "\n".join(f"{c['t']} L2={len(c['kids'])} L3={sum(len(s['kids']) for s in c['kids'])}" for c in tree["kids"])
    )
    (ROOT / "_jd_tree_stats.txt").write_text(stats, encoding="utf-8")
    print(stats)
    print("wrote", out, "bytes", out.stat().st_size)


if __name__ == "__main__":
    main()
