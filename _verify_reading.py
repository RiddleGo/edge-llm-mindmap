# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
t = Path(r"D:/推理VS训练/端侧部署思维导图.html").read_text(encoding="utf-8")
for s in [
    "bindViewport", "applyTransform", "map-workspace", "reader-label",
    'getElementById("detail")', 'getElementById("mapBoard")', 'id="mapCanvas"',
    'class="tool"', 'class="map-hint"', "col-label", "l3-grid", "key-1",
    "has-kids", "spaceDown", "map-workspace",
]:
    print(s, t.count(s))
lines = t.splitlines()
for i, l in enumerate(lines, 1):
    if 620 <= i <= 710 and len(l) < 220:
        print(f"{i}|{l}")
idx = t.find("applyTransform()")
print("--- applyTransform ---")
print(t[idx : idx + 400])
idx = t.find("bindViewport()")
print("--- bindViewport head ---")
print(t[idx : idx + 500])
