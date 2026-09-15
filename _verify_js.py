# -*- coding: utf-8 -*-
import sys, re
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
t = Path(r"D:/推理VS训练/端侧部署思维导图.html").read_text(encoding="utf-8")
# Map app object name and methods
for pat in [r"const Map\w+\s*=", r"window\.Map\w+", r"toggleRoot|toggleRoot|openRoot", r"fillList|fillList", r"\.render\s*\("]:
    print(pat, re.findall(pat, t)[:8])
# find init at end
idx = t.rfind("MapApp")
print("last MapApp", idx)
print(t[idx:idx+200] if idx>0 else "none")
# also MindMap / TreeApp
for name in ["MapApp", "MindMap", "TreeApp", "MapUI", "app ="]:
    print(name, t.count(name))
# show end of file
print("--- tail ---")
print(t[-1200:])
