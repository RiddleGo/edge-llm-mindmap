# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
p = Path(r"D:/推理VS训练") / "端侧部署思维导图.html"
t = p.read_text(encoding="utf-8")

m = re.search(r'<div class="map-hint">[^<]*</div>', t)
print("found", m.group(0) if m else None)
if m:
    neu = '<div class="map-hint">左侧点目录 · 列表内滚动 · 拖中间竖线调左右宽度 · 右侧读讲义</div>'
    t = t[: m.start()] + neu + t[m.end() :]
    p.write_text(t, encoding="utf-8")
    print("hint updated")

t = p.read_text(encoding="utf-8")
print("title", re.search(r"--fs-detail-title:\s*[^;]+", t).group(0))
print("detail h3 weight", "font-weight: 600" in t[t.find(".detail h3") : t.find(".detail h3") + 200])
print("split css", ".split-handle {" in t)
print("split html", 'id="splitHandle"' in t and 'class="split-handle"' in t)
print("bindSplitter", "bindSplitter()" in t)
print("setReaderWidth", "setReaderWidth" in t)
