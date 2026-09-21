# -*- coding: utf-8 -*-
"""自己改完 md 之后运行：重建思维导图并推到 GitHub Pages。

推送靠本机已登录的 GitHub CLI（gh），不会也不应把 token 写进仓库。
新电脑只需第一次：gh auth login
"""
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


def ensure_gh_login() -> None:
    p = subprocess.run(
        ["gh", "auth", "status"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if p.returncode == 0:
        print("GitHub 已登录，可以推送。")
        return
    print("还没登录 GitHub CLI，无法一键推送。")
    print("请在本机终端执行一次（只需一次）：")
    print("  gh auth login")
    print("选 GitHub.com → HTTPS → 浏览器登录。")
    print("登录后再运行：python 更新网页.py")
    print("说明：token 不能写进仓库，否则网上谁都能拿走改你的库。")
    raise SystemExit(1)


def main() -> None:
    ensure_gh_login()
    print("1/5 从《端侧模型部署.md》生成主线树（原文直灌，不加厚改写）")
    run("build_mindmap_tree.py")
    print("2/5 写入主线 HTML")
    run("_inject_main_tree.py")
    print("3/5 从《JD能力缺口补全.md》生成 JD 树")
    run("build_jd_gap_tree.py")
    print("4/5 写入 JD HTML")
    run("_refresh_jd_tree.py")
    print("5/5 推到 GitHub Pages")
    run("_push_jd_update.py")
    print("完成。一两分钟后刷新 https://riddlego.github.io/edge-llm-mindmap/")


if __name__ == "__main__":
    main()
