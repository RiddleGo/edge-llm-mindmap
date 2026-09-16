# -*- coding: utf-8 -*-
"""Build jd-gap-tree.json from JD能力缺口补全.md"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MD = ROOT / "JD能力缺口补全.md"


def short(s: str, n: int = 80) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    return s if len(s) <= n else s[: n - 1] + "…"


def main() -> None:
    text = MD.read_text(encoding="utf-8")
    text = "".join(p if i % 2 == 0 else "" for i, p in enumerate(text.split("```")))
    tree = {
        "id": "root",
        "t": "JD 能力缺口补全",
        "d": "与端侧主线并列。补指令流水、DSA/内存层次、DeepSeek MLA、框架源码向、TGI、Glow、RISC-V、集合通信、云 Serving。",
        "kids": [],
        "w": "投递/面试缺哪块补哪块，不替代端侧连载。",
        "b": "",
        "k": 0,
    }
    cur1 = cur2 = None
    term_re = re.compile(r"^- \*\*(.+?)\*\*\s*[—–:：]\s*(.+)$")

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
        }
        cur1["kids"].append(cur2)

    def add_l3(title: str, desc: str = "") -> None:
        if not cur2:
            return
        t = short(title, 28)
        if any(k["t"] == t for k in cur2["kids"]):
            return
        cur2["kids"].append(
            {
                "id": f"{cur2['id']}-{len(cur2['kids'])+1}",
                "t": t,
                "d": short(desc, 160) if desc else short(title, 120),
                "kids": [],
                "w": short(f"弄清「{t}」，对标 JD 时才知道缺口在哪。", 60),
                "b": "",
                "k": 0,
            }
        )

    for raw in text.splitlines():
        line = raw.rstrip()
        if re.match(r"^##\s+", line):
            new_l1(line[3:].strip())
            continue
        if re.match(r"^###\s+", line) and cur1:
            new_l2(line[4:].strip())
            continue
        if not cur1:
            continue
        if not cur2:
            if line and not line.startswith(("#", "|", ">", "-", "*")) and not cur1["d"]:
                cur1["d"] = short(line, 140)
            continue
        if line and not line.startswith(("#", "|", ">", "-", "*")) and not cur2.get("d"):
            cur2["d"] = short(line, 160)
        tm = term_re.match(line)
        if tm:
            add_l3(tm.group(1), tm.group(2))
            continue
        if line.startswith("- "):
            body = line[2:].strip()
            body = re.sub(r"^\*\*(.+?)\*\*\s*", r"\1 ", body)
            add_l3(body[:28], body)

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
                120,
            )
        for j, c2 in enumerate(c1["kids"], 1):
            c2["t"] = f"{i}.{j} · {c2['t']}"
            if not c2.get("w"):
                c2["w"] = short(f"服务「{c1['t']}」落地。", 50)
            if not c2.get("b"):
                themes = [x["t"] for x in c2["kids"][:4]]
                c2["b"] = short(
                    f"补主线未写透的一块。下含：{'、'.join(t.split(' · ')[-1] for t in themes) or '子点'}。",
                    120,
                )
            if not c2["kids"]:
                c2["kids"].append(
                    {
                        "id": f"{c2['id']}-n",
                        "t": f"{i}.{j}.1 · {c2['t'].split(' · ', 1)[-1]}",
                        "d": c2.get("d") or "见 JD能力缺口补全.md",
                        "kids": [],
                        "w": c2.get("w") or "",
                        "b": "",
                        "k": 0,
                    }
                )
            else:
                for k, leaf in enumerate(c2["kids"], 1):
                    leaf["t"] = f"{i}.{j}.{k} · {re.sub(r'^\\d+(?:\\.\\d+)*\\s*·\\s*', '', leaf['t'])}"

    out = ROOT / "jd-gap-tree.json"
    out.write_text(json.dumps(tree, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    stats = (
        f"L1={len(tree['kids'])} "
        f"L2={sum(len(c['kids']) for c in tree['kids'])} "
        f"L3={sum(len(s['kids']) for c in tree['kids'] for s in c['kids'])}\n"
        + "\n".join(
            f"{c['t']} L2={len(c['kids'])}" for c in tree["kids"]
        )
    )
    (ROOT / "_jd_tree_stats.txt").write_text(stats, encoding="utf-8")
    print(stats)
    print("wrote", out, "bytes", out.stat().st_size)


if __name__ == "__main__":
    main()
