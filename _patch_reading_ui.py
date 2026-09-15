# -*- coding: utf-8 -*-
"""Reading-first redesign for 端侧部署思维导图.html"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HTML = Path(r"D:/推理VS训练") / "端侧部署思维导图.html"
text = HTML.read_text(encoding="utf-8")
assert "/* === MAP SLIDE === */" in text or "MAP SLIDE" in text

# --- tokens ---
repls = [
    ("--node-inactive-opacity: 0.55;", "--node-inactive-opacity: 0.78;"),
    ("--fs-detail-title: 22px;", "--fs-detail-title: 26px;"),
    ("--fs-detail-body: 16px;", "--fs-detail-body: 17px;"),
    ("--text-muted: #7a8f82;", "--text-muted: #93a89c;"),
    ("--col-gap: 40px;", "--col-gap: 18px;"),
    ("--node-gap: 12px;", "--node-gap: 8px;"),
]
for a, b in repls:
    if a in text:
        text = text.replace(a, b, 1)
        print("token", a[:28], "-> ok")
    else:
        print("token miss", a[:40])

NEW_CSS = r'''/* === MAP SLIDE — reading-first === */
.map-top {
    position: absolute; left: 36px; right: 36px; top: 14px; height: 52px;
    display: flex; align-items: center; gap: 10px; z-index: 6;
}
.map-top h2 {
    flex: 0 0 auto;
    font-family: var(--font-display); font-size: 24px; font-weight: 800;
    letter-spacing: -0.01em; margin-right: 10px; color: var(--text-primary);
}
.crumb {
    flex: 1 1 auto; min-width: 0;
    font-family: var(--font-body); font-size: 14px; font-weight: 400;
    color: var(--text-muted); line-height: 1.4;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    margin-right: 8px;
}
.tool {
    flex: 0 0 auto; white-space: nowrap;
    border: 1px solid var(--accent-dim); background: var(--node-bg);
    color: var(--text-leaf); font: 500 12px/1 var(--font-mono);
    padding: 8px 12px; cursor: pointer;
    transition: border-color 0.2s ease, color 0.2s ease;
}
.tool.on, .tool:hover { border-color: var(--accent-bright); color: var(--accent-bright); }

.map-hint {
    position: absolute; left: 36px; right: 36px; top: 66px;
    font-family: var(--font-mono); font-size: 12px; font-weight: 400;
    color: var(--text-muted); letter-spacing: 0.03em; line-height: 1.4;
    opacity: 0.92; pointer-events: none; z-index: 6;
}

.map-legend {
    flex: 0 0 auto;
    display: flex; align-items: center; gap: 8px;
    font-family: var(--font-mono); font-size: 11px;
    color: var(--text-muted); white-space: nowrap; margin-right: 4px;
}
.map-legend .dot {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    margin-right: 3px; vertical-align: middle; background: var(--accent);
}
.map-legend .dot.key1 { background: var(--key-1); }
.map-legend .dot.key2 { background: var(--key-2); }

/* Left browser + right reader */
.map-workspace {
    position: absolute; left: 0; top: 90px; right: 0; bottom: 0;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 540px;
    gap: 0;
    overflow: hidden;
    background: var(--slide-bg);
}
.map-board {
    position: relative;
    overflow: auto;
    cursor: default;
    touch-action: pan-x pan-y;
    user-select: none;
    padding: 10px 16px 28px 36px;
    scrollbar-width: thin;
    scrollbar-color: var(--accent-dim) transparent;
    overscroll-behavior: contain;
}
.map-board.space-pan { cursor: grab; }
.map-board.is-panning { cursor: grabbing; }
.map-board svg { max-width: none; max-height: none; }

#mapCanvas {
    position: relative;
    left: 0; top: 0;
    min-width: 100%;
    min-height: 100%;
    transform-origin: 0 0;
}
#wires {
    position: absolute; inset: 0; width: 100%; height: 100%;
    pointer-events: none; overflow: visible; opacity: 0.45;
}
.cols {
    position: relative; left: 0; top: 4px;
    display: flex; flex-direction: row; gap: var(--col-gap); align-items: flex-start;
    width: max-content;
    min-width: calc(100% - 20px);
    height: auto;
    overflow: visible;
    padding-bottom: 16px;
}
.cols.ttb {
    flex-direction: column; gap: 14px;
    width: calc(100% - 20px);
}
.col {
    flex: 0 0 auto; min-width: 220px;
    display: none; flex-direction: column; gap: 8px;
    opacity: 0; pointer-events: none;
    transform: translateX(-14px);
    transition: opacity 0.32s var(--ease-out-expo), transform 0.32s var(--ease-out-expo);
}
.col.show {
    display: flex; opacity: 1; pointer-events: auto; transform: none;
}
#col0.show { width: 250px; min-width: 250px; max-width: 250px; }
#col1.show { width: 292px; min-width: 292px; max-width: 292px; }
#col2.show { width: 292px; min-width: 292px; max-width: 292px; }
#col3.show { width: 400px; min-width: 400px; max-width: 420px; }
.cols.ttb #col0.show,
.cols.ttb #col1.show,
.cols.ttb #col2.show,
.cols.ttb #col3.show { width: 100%; min-width: 0; max-width: none; }
.cols.ttb .col {
    transform: translateY(-10px);
    flex-direction: row; flex-wrap: wrap; align-content: flex-start;
}
.cols.ttb .col.show { transform: none; }

.col-label {
    font-family: var(--font-mono);
    font-size: var(--fs-label); font-weight: 500;
    letter-spacing: 0.1em; color: var(--accent-bright);
    min-height: 18px; flex: 0 0 auto;
    opacity: 0.88; line-height: 1.35; margin-bottom: 2px;
}

/* Directory cards: title only */
.node {
    border: 1px solid rgba(22, 101, 52, 0.7);
    background: var(--node-bg);
    color: var(--text-leaf);
    font-family: var(--font-body);
    font-size: var(--fs-topic); font-weight: 500; line-height: 1.35;
    padding: 10px 28px 10px 12px;
    cursor: pointer;
    text-align: left;
    width: 100%;
    position: relative;
    transition: border-color 0.15s ease, background 0.15s ease, opacity 0.2s ease;
    word-break: break-word;
    box-shadow: none;
}
.col.show .node:not(.active):not(.root-node) { opacity: var(--node-inactive-opacity); }
.cols.ttb .node { width: auto; min-width: 190px; max-width: 320px; }
.node:hover {
    border-color: var(--accent);
    opacity: 1;
}
.node.active {
    opacity: 1;
    background: var(--node-active);
    border-color: var(--accent-bright);
    color: #f0fdf4;
    font-weight: 600;
    box-shadow: inset 0 0 0 1px rgba(134, 239, 172, 0.16);
}
.node.key-1 {
    border-color: rgba(251, 191, 36, 0.45);
    border-left: 3px solid var(--key-1);
}
.node.key-2 {
    border-color: rgba(251, 113, 133, 0.45);
    border-left: 3px solid var(--key-2);
}
.node.key-1:hover { border-color: var(--key-1); }
.node.key-2:hover { border-color: var(--key-2); }
.node.key-1.active {
    background: var(--key-1-bg);
    border-color: var(--key-1);
    color: #fffbeb;
}
.node.key-2.active {
    background: var(--key-2-bg);
    border-color: var(--key-2);
    color: #fff1f2;
}
.node.key-1::before,
.node.key-2::before {
    position: absolute; top: 4px; left: 8px;
    font-family: var(--font-mono);
    font-size: 9px; font-weight: 600; line-height: 1;
    letter-spacing: 0.04em; pointer-events: none; opacity: 0.85;
}
.node.key-1::before { content: "重点"; color: var(--key-1); }
.node.key-2::before { content: "核心"; color: var(--key-2); }
.node.key-1, .node.key-2 { padding-top: 16px; }

.node.root-node {
    font-family: var(--font-display); font-weight: 800;
    font-size: 20px; line-height: 1.28;
    padding: 18px 14px; text-align: center; min-height: 88px;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.node.root-node .sub {
    display: block !important;
    margin-top: 8px;
    font-family: var(--font-mono);
    font-size: 11px; font-weight: 400;
    color: var(--text-muted); line-height: 1.4;
}
.node .sub { display: none; }

#list1 .node {
    font-size: var(--fs-chapter); font-weight: 600;
    padding: 10px 28px 10px 12px;
}
#list2 .node {
    font-size: var(--fs-topic); font-weight: 500;
    padding: 9px 28px 9px 12px;
}
#list3 .node {
    font-size: var(--fs-term); font-weight: 400;
    padding: 9px 12px;
    display: block;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
#list1 .node.key-1, #list1 .node.key-2,
#list2 .node.key-1, #list2 .node.key-2,
#list3 .node.key-1, #list3 .node.key-2 { padding-top: 16px; }

#list1, #list2, #list3 {
    max-height: 760px;
    overflow-y: auto; overflow-x: hidden;
    padding-right: 4px;
    scrollbar-width: thin;
    scrollbar-color: var(--accent-dim) transparent;
    overscroll-behavior: contain;
}
.node.has-kids::after {
    content: "▸";
    position: absolute; right: 10px; top: 50%;
    transform: translateY(-50%);
    color: var(--accent-bright); font-size: 11px;
    font-family: var(--font-mono); opacity: 0.75;
}
.cols.ttb .node.has-kids::after { content: "▾"; top: 10px; transform: none; }
.node, .pager, .tool { cursor: pointer; }
.list {
    display: flex; flex-direction: column; gap: var(--node-gap);
    flex: 0 0 auto; overflow: visible;
}
.cols.ttb .list { flex-direction: row; flex-wrap: wrap; width: 100%; gap: 8px; }
.l3-grid, .l3-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: var(--node-gap);
}
.cols.ttb .l3-grid { grid-template-columns: repeat(3, 1fr); width: 100%; }

/* Reader — primary reading surface */
.reader {
    border-left: 1px solid rgba(74, 222, 128, 0.22);
    background: linear-gradient(180deg, #0a1210 0%, #070b0c 100%);
    padding: 18px 26px 26px;
    overflow: hidden;
    display: flex; flex-direction: column;
    min-width: 0;
}
.reader-label {
    font-family: var(--font-mono);
    font-size: 11px; font-weight: 600;
    letter-spacing: 0.14em;
    color: var(--accent-bright);
    margin-bottom: 12px;
    opacity: 0.92;
    flex: 0 0 auto;
}
.detail {
    border: none; background: transparent; padding: 0;
    min-height: 0; max-height: none; max-width: 100%;
    overflow-y: auto; overscroll-behavior: contain;
    flex: 1 1 auto;
    scrollbar-width: thin;
    scrollbar-color: var(--accent-dim) transparent;
}
.detail h3 {
    font-family: var(--font-display);
    font-size: var(--fs-detail-title); font-weight: 800;
    line-height: 1.28; margin-bottom: 16px;
    color: var(--text-primary);
    letter-spacing: -0.01em;
}
.detail > p {
    font-family: var(--font-body);
    font-size: var(--fs-detail-body);
    line-height: 1.78; color: var(--text-leaf);
    max-width: 40em;
}
.explain-block { margin-top: 0; max-width: 40em; }
.explain-label {
    font-family: var(--font-mono);
    font-size: 11px; font-weight: 600;
    letter-spacing: 0.12em;
    color: var(--accent-bright);
    margin: 18px 0 8px;
    padding-bottom: 5px;
    border-bottom: 1px solid rgba(74, 222, 128, 0.18);
}
.explain-label:first-child { margin-top: 0; }
.explain-label.explain-bridge {
    color: var(--bridge);
    border-bottom-color: rgba(103, 232, 249, 0.22);
}
.explain-block p {
    margin: 0;
    font-family: var(--font-body);
    font-size: var(--fs-detail-body);
    line-height: 1.8;
    color: var(--text-leaf);
}
.explain-block .bridge-text { color: #a5f3fc; }
.explain-block .meta-line {
    margin-top: 22px;
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--text-muted);
    line-height: 1.5;
}
.pager {
    display: flex; gap: 8px; align-items: center;
    font-family: var(--font-mono);
    font-size: 12px; color: var(--text-muted);
    margin-top: 4px;
}

'''

# Also support key-1/key-2 class names used by JS (key-1)
NEW_CSS += """
.node.key-1 { border-color: rgba(251, 191, 36, 0.45); border-left: 3px solid var(--key-1); }
.node.key-2 { border-color: rgba(251, 113, 133, 0.45); border-left: 3px solid var(--key-2); }
.node.key-1:hover { border-color: var(--key-1); }
.node.key-2:hover { border-color: var(--key-2); }
.node.key-1.active { background: var(--key-1-bg); border-color: var(--key-1); color: #fffbeb; }
.node.key-2.active { background: var(--key-2-bg); border-color: var(--key-2); color: #fff1f2; }
.node.key-1::before, .node.key-2::before {
    position: absolute; top: 4px; left: 8px;
    font-family: var(--font-mono); font-size: 9px; font-weight: 600; line-height: 1;
    letter-spacing: 0.04em; pointer-events: none; opacity: 0.85;
}
.node.key-1::before { content: "重点"; color: var(--key-1); }
.node.key-2::before { content: "核心"; color: var(--key-2); }
.node.key-1, .node.key-2 { padding-top: 16px; }
#list1 .node.key-1, #list1 .node.key-2,
#list2 .node.key-1, #list2 .node.key-2,
#list3 .node.key-1, #list3 .node.key-2 { padding-top: 16px; }
.node.has-kids::after {
    content: "▸";
    position: absolute; right: 10px; top: 50%;
    transform: translateY(-50%);
    color: var(--accent-bright); font-size: 11px;
    font-family: var(--font-mono); opacity: 0.75;
}
.l3-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: var(--node-gap);
}
"""

# Replace from MAP SLIDE marker to just before .edit-hotzone / .edit-toggle
start = text.find("/* === MAP SLIDE === */")
# Prefer ending at .edit-hotzone or .edit-toggle CSS
end_candidates = []
for marker in ("\n.edit-hotzone {", "\n.edit-toggle {", "\nbody.editing"):
    idx = text.find(marker, start)
    if idx > 0:
        end_candidates.append(idx)
if not end_candidates:
    raise SystemExit("cannot find end of map css")
end = min(end_candidates)
text = text[:start] + NEW_CSS + text[end:]
print("CSS swapped", start, end)

# --- HTML: hint ---
text = re.sub(
    r'<div class="map-hint">[^<]*</div>',
    '<div class="map-hint">左侧点目录导航 · 列表内滚动 · 右侧读讲义（是什么 / 作用 / 承接）</div>',
    text,
    count=1,
)

# --- HTML: workspace + move detail to reader ---
old_map = re.search(
    r'<div class="map-board" id="mapBoard">.*?</section>',
    text,
    flags=re.S,
)
if not old_map:
    raise SystemExit("map-board block not found")

new_map_html = '''<div class="map-workspace">
      <div class="map-board" id="mapBoard">
        <div id="mapCanvas">
        <svg id="wires" viewBox="0 0 1920 988" preserveAspectRatio="none"></svg>
        <div class="cols" id="cols">
          <div class="col show" id="col0">
            <div class="col-label">根 · 总览</div>
            <button class="node root-node has-kids" id="rootNode" type="button" data-id="root" data-depth="0">端侧大模型部署<span class="sub">点开后按 1→2→3… 讲</span></button>
          </div>
          <div class="col" id="col1"><div class="col-label">章 · 1 2 3…</div><div class="list" id="list1"></div></div>
          <div class="col" id="col2"><div class="col-label">主题 · 1.1 1.2…</div><div class="list" id="list2"></div></div>
          <div class="col" id="col3">
            <div class="col-label">知识点 · 1.1.1…</div>
            <div class="l3-grid" id="list3"></div>
            <div class="pager" id="pager"></div>
          </div>
        </div>
        </div>
      </div>
      <aside class="reader" aria-label="讲义">
        <div class="reader-label">讲义 · 是什么 / 作用 / 承接</div>
        <div class="detail" id="detail">
          <h3>从左边开始</h3>
          <p>点根节点 → 选一章 → 选主题 → 选知识点。目录只负责导航，说明都在右侧阅读。</p>
        </div>
      </aside>
    </div>
    </section>'''

text = text[: old_map.start()] + new_map_html + text[old_map.end() :]
print("HTML workspace injected")

# --- title lead ---
text = re.sub(
    r'(<p class="title-lead reveal">)[^<]*(</p>)',
    r"\1左边点目录，右边读讲义：是什么、起什么作用、和前后怎么接。重点琥珀、核心珊瑚。\2",
    text,
    count=1,
)

# --- JS: slim fillList ---
text2, n = re.subn(
    r"let sub = \"\";\n\s*if \(depth === 1 && n\.d\) sub = `<span class=\"sub\">\$\{esc\(n\.d\)\}</span>`;\n\s*else if \(depth === 2 && \(n\.b \|\| n\.d\)\) sub = `<span class=\"sub\">\$\{esc\(n\.b \|\| n\.d\)\}</span>`;\n\s*else if \(depth === 3 && n\.d\) sub = `<span class=\"sub\">\$\{esc\(n\.d\)\}</span>`;\n\s*b\.innerHTML = `\$\{esc\(n\.t\)\}\$\{sub\}`;",
    "b.innerHTML = esc(n.t);",
    text,
    count=1,
)
if n:
    text = text2
    print("fillList slimmed")
else:
    text2, n = re.subn(
        r"let sub = \"\";.*?b\.innerHTML = `\$\{esc\(n\.t\)\}\$\{sub\}`;",
        "b.innerHTML = esc(n.t);",
        text,
        count=1,
        flags=re.S,
    )
    if n:
        text = text2
        print("fillList slimmed alt")
    else:
        print("WARN fillList not slimmed")

# --- JS: replace bindViewport ---
# Actual method name from file: bindViewport
m = re.search(r"bindViewport\(\)\s*\{", text)
if not m:
    raise SystemExit("bindViewport not found")
# walk braces
i = text.find("{", m.start())
depth = 0
while i < len(text):
    if text[i] == "{":
        depth += 1
    elif text[i] == "}":
        depth -= 1
        if depth == 0:
            end = i
            break
    i += 1
else:
    raise SystemExit("brace fail")

NEW_BIND = r'''bindViewport() {
        const board = document.getElementById("mapBoard");
        // Reading-first: native scroll. Space+drag pans the browser pane only.
        let spaceDown = false;
        let drag = null;
        window.addEventListener("keydown", (e) => {
            if (e.code !== "Space" || e.repeat) return;
            const t = e.target;
            if (t && (t.isContentEditable || ["INPUT","TEXTAREA","BUTTON"].includes(t.tagName))) return;
            spaceDown = true;
            board.classList.add("space-pan");
            e.preventDefault();
        });
        window.addEventListener("keyup", (e) => {
            if (e.code === "Space") {
                spaceDown = false;
                board.classList.remove("space-pan");
            }
        });
        board.addEventListener("pointerdown", (e) => {
            if (!spaceDown) return;
            if (e.pointerType === "mouse" && e.button !== 0) return;
            drag = { id: e.pointerId, x: e.clientX, y: e.clientY, sl: board.scrollLeft, st: board.scrollTop };
            board.classList.add("is-panning");
            try { board.setPointerCapture(e.pointerId); } catch (_) {}
            e.preventDefault();
        });
        board.addEventListener("pointermove", (e) => {
            if (!drag || e.pointerId !== drag.id) return;
            board.scrollLeft = drag.sl - (e.clientX - drag.x);
            board.scrollTop = drag.st - (e.clientY - drag.y);
        });
        const endDrag = (e) => {
            if (!drag || e.pointerId !== drag.id) return;
            drag = null;
            board.classList.remove("is-panning");
        };
        board.addEventListener("pointerup", endDrag);
        board.addEventListener("pointercancel", endDrag);
        board.addEventListener("wheel", (e) => {
            if (e.ctrlKey || e.metaKey) {
                e.preventDefault();
                const old = this.view.scale || 1;
                const factor = e.deltaY < 0 ? 1.06 : 1 / 1.06;
                const next = Math.min(this.maxScale || 1.6, Math.max(this.minScale || 0.75, old * factor));
                this.view.scale = next;
                this.view.x = 0; this.view.y = 0;
                this.applyTransform();
            }
            // else: native scroll on board / lists
        }, { passive: false });
    }'''

text = text[: m.start()] + NEW_BIND + text[end + 1 :]
print("bindViewport replaced")

# applyTransform: prefer scale-only / none
text = text.replace(
    "el.style.transform = `translate(${this.view.x}px, ${this.view.y}px) scale(${this.view.scale})`;",
    'el.style.transform = (!this.view.scale || this.view.scale === 1) ? "none" : `scale(${this.view.scale})`;',
)

# resetView should also reset board scroll
if "resetView()" in text and "board.scrollLeft = 0" not in text:
    text = text.replace(
        """resetView() {
        this.view = { x: 0, y: 0, scale: 1 };
        this.applyTransform();
        this.drawWires();
    },""",
        """resetView() {
        this.view = { x: 0, y: 0, scale: 1 };
        const board = document.getElementById("mapBoard");
        if (board) { board.scrollLeft = 0; board.scrollTop = 0; }
        this.applyTransform();
        this.drawWires();
    },""",
    )

# Default empty detail copy in render fallback
text = text.replace(
    'detail.innerHTML = `<h3>尚未选择知识点</h3><p>先点根节点，再点一章、一个主题，最后点知识点查看要点。</p>`;',
    'detail.innerHTML = `<h3>从左边开始</h3><p>点根节点 → 选一章 → 选主题 → 选知识点。目录只负责导航，说明都在右侧阅读。</p>`;',
)

HTML.write_text(text, encoding="utf-8")
print("wrote", HTML.stat().st_size)

# checks
t = HTML.read_text(encoding="utf-8")
checks = {
    "workspace": "map-workspace" in t,
    "reader": '<aside class="reader"' in t,
    "detail once": t.count('id="detail"') == 1,
    "css fixed": ".map-board {\n    position: absolute; left: 0; top: 112px; right: 0; bottom: 0;\n.map-top h2" not in t,
    "spaceDown": "spaceDown" in t,
    "slim cards": "b.innerHTML = esc(n.t)" in t,
    "reader-label": "reader-label" in t,
}
for k, v in checks.items():
    print(("OK" if v else "FAIL"), k)
