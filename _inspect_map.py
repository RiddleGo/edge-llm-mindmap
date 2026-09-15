# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
p = Path(r"D:/推理VS训练") / "端侧部署思维导图.html"
text = p.read_text(encoding="utf-8")
for s in [
    "MAP SLIDE", "map-board", "map-hint", "mapSlide", "bindViewport",
    "bindViewport", "fillList", "fillList", "explainBlock", 'id="detail"',
    "deck-controls", "edit-hotzone", "map-workspace", "map-top", "mapBoard",
    "applyTransform", "boardScale", "spaceDown",
]:
    print(repr(s), text.find(s))

lines = text.splitlines()
print("total lines", len(lines))
for i, l in enumerate(lines, 1):
    if (255 <= i <= 290) or (600 <= i <= 665) or (800 <= i <= 920) or (930 <= i <= 980):
        if len(l) < 180:
            print(f"{i}|{l}")
        else:
            print(f"{i}|LONG {len(l)}")
