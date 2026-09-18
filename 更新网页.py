# -*- coding: utf-8 -*-
"""自己改完 md 之后，双击或运行本文件：重建思维导图并推到 GitHub Pages。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def run(script: str) -> None:
    p = subprocess.run([PY, str(ROOT / script)], cwd=ROOT)
    if p.returncode != 0:
        raise SystemExit(f"失败：{script}（退出码 {p.returncode}）")


def main() -> None:
    print("1/5 从《端侧模型部署.md》生成主线树")
    run("build_mindmap_tree.py")
    print("2/5 灌讲义、加厚叶子")
    run("_enrich_content_v2.py")
    run("_thicken_leaves.py")
    run("_batch_fill_leaves.py")
    print("3/5 从《JD能力缺口补全.md》生成 JD 树")
    run("build_jd_gap_tree.py")
    print("4/5 写入 HTML")
    run("_refresh_jd_tree.py")
    print("5/5 推到 GitHub Pages")
    run("_push_jd_update.py")
    print("完成。一两分钟后刷新 https://riddlego.github.io/edge-llm-mindmap/")


if __name__ == "__main__":
    main()
