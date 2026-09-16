# -*- coding: utf-8 -*-
"""Add dual TAB (端侧主线 / JD补全) to mindmap HTML."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"D:\推理VS训练")
HTML = ROOT / "端侧部署思维导图.html"
JD_TREE = ROOT / "jd-gap-tree.json"


def main() -> None:
    text = HTML.read_text(encoding="utf-8")
    jd = JD_TREE.read_text(encoding="utf-8").strip()

    # 1) CSS for tabs
    css = """
/* === Curriculum tabs === */
.curr-tabs {
    flex: 0 0 auto;
    display: inline-flex;
    gap: 0;
    margin-right: 10px;
    border: 1px solid var(--accent-dim);
    background: var(--node-bg);
}
.curr-tab {
    border: 0;
    background: transparent;
    color: var(--text-muted);
    font: 600 12px/1 var(--font-mono);
    padding: 8px 14px;
    cursor: pointer;
    letter-spacing: 0.02em;
}
.curr-tab.on {
    color: #04110a;
    background: var(--accent);
}
.curr-tab:hover:not(.on) { color: var(--accent-bright); }
"""
    if "/* === Curriculum tabs === */" not in text:
        text = text.replace("</style>", css + "\n</style>", 1)

    # 2) Tab buttons in map-top (after h2)
    if 'id="tabMain"' not in text:
        old = '<div class="map-top">\n        <h2>知识树</h2>'
        new = (
            '<div class="map-top">\n'
            '        <h2>知识树</h2>\n'
            '        <div class="curr-tabs" role="tablist" aria-label="课程页">\n'
            '          <button class="curr-tab on" id="tabMain" type="button" role="tab" aria-selected="true">端侧主线</button>\n'
            '          <button class="curr-tab" id="tabJd" type="button" role="tab" aria-selected="false">JD补全</button>\n'
            "        </div>"
        )
        if old not in text:
            raise SystemExit("map-top h2 anchor missing")
        text = text.replace(old, new, 1)

    # 3) Rename const TREE → TREE_MAIN + inject TREE_JD + let TREE
    if "const TREE_MAIN" not in text:
        m = re.search(r"const TREE = (\{.*?\});", text, re.S)
        if not m:
            raise SystemExit("const TREE = {...} not found")
        main_json = m.group(1)
        replacement = (
            f"const TREE_MAIN = {main_json};\n"
            f"const TREE_JD = {jd};\n"
            "let TREE = TREE_MAIN;\n"
            'let CURR = "main";'
        )
        text = text[: m.start()] + replacement + text[m.end() :]

    # 4) Tab switch JS — before </script> of main, after map object exists
    hook = """
/* === Curriculum tab switch === */
(function setupCurrTabs() {
    const tabMain = document.getElementById("tabMain");
    const tabJd = document.getElementById("tabJd");
    if (!tabMain || !tabJd || !window.__mapApp) return;
    const app = window.__mapApp;
    const rootBtn = document.getElementById("rootNode");
    const crumb = document.getElementById("crumb");
    const detail = document.getElementById("detail");
    const hint = document.querySelector(".map-hint");
    function applyTree(which) {
        CURR = which;
        TREE = which === "jd" ? TREE_JD : TREE_MAIN;
        tabMain.classList.toggle("on", which === "main");
        tabJd.classList.toggle("on", which === "jd");
        tabMain.setAttribute("aria-selected", which === "main" ? "true" : "false");
        tabJd.setAttribute("aria-selected", which === "jd" ? "true" : "false");
        if (rootBtn) {
            const sub = which === "jd"
                ? "对标招聘缺口 · 与主线并列"
                : "点开后按 1→2→3… 讲";
            rootBtn.innerHTML = (TREE.t || "知识树") + '<span class="sub">' + sub + "</span>";
        }
        if (crumb) crumb.textContent = TREE.t || "根节点";
        if (detail) {
            detail.innerHTML = which === "jd"
                ? "<h3>JD 补全</h3><p>本页补主线未写透的缺口：指令流水、DeepSeek MLA、框架源码向、TGI、Glow、RISC-V、集合通信、云 Serving。点左边目录阅读。</p>"
                : "<h3>从左边开始</h3><p>点根节点 → 选一章 → 选主题 → 选知识点。目录只负责导航，说明都在右侧阅读。</p>";
        }
        if (hint) {
            hint.textContent = which === "jd"
                ? "当前：JD补全 · 与端侧主线并列 · 不替代连载顺序"
                : "左侧点目录 · 列表内滚动 · 拖中间竖线调左右宽度 · 右侧读讲义";
        }
        if (typeof app.reset === "function") app.reset();
        else if (typeof app.render === "function") {
            app.open = false;
            app.path = [];
            app.render();
        }
    }
    tabMain.onclick = () => applyTree("main");
    tabJd.onclick = () => applyTree("jd");
})();
"""
    if "setupCurrTabs" not in text:
        # expose map app
        # find: new Something that owns fillList — look for assignment
        if "window.__mapApp" not in text:
            var = "MapApp"
            expose = f"\nwindow.__mapApp = {var};\n"
            # Place expose just before curriculum tab hook insert point (end of script)
            insert_at = text.rfind("</script>")
            text = text[:insert_at] + expose + hook + text[insert_at:]
        else:
            insert_at = text.rfind("</script>")
            text = text[:insert_at] + hook + text[insert_at:]

    HTML.write_text(text, encoding="utf-8")
    # sync index
    (ROOT / "index.html").write_text(text, encoding="utf-8")
    print("patched", HTML.name, "size", HTML.stat().st_size)
    print("TREE_MAIN", "TREE_MAIN" in text, "TREE_JD", "const TREE_JD" in text)
    print("tabs", 'id="tabJd"' in text, "hook", "setupCurrTabs" in text)


if __name__ == "__main__":
    main()
