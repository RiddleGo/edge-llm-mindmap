# -*- coding: utf-8 -*-
"""Enrich mindmap-tree.json with teaching fields d/w/b/k; inject HTML."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"D:\推理VS训练")
TREE_JSON = ROOT / "mindmap-tree.json"
HTML = ROOT / "端侧部署思维导图.html"

NUM_PREFIX = re.compile(r"^\d+(?:\.\d+)*\s*[·.\s、\-–—]+\s*")

# ---- keyword sets for k (tune: ~15–25% leaves, fewer L2) ----
K2_EXACT = {
    "kv cache", "kv-cache", "transformer", "attention", "self-attention",
    "prefill", "decode", "ttft", "onnx", "tensorrt", "qnn",
    "int8", "fp16", "scale", "zero-point", "zero point", "zeropoint",
    "算子融合", "蒸馏", "知识蒸馏", "门禁", "校准", "量化",
}
K2_PHRASE = (
    "kv cache", "kv-cache", "zero-point", "zero point", "算子融合",
    "知识蒸馏", "self-attention", "multi-head", "多头注意力",
    "首字延迟", "首 token", "首token",
)
K1_TOKENS = {
    "ptq", "qat", "gptq", "awq", "smoothquant", "gguf", "llama.cpp",
    "profiling", "softmax", "layernorm", "gemm", "flashattention",
    "gqa", "mqa", "mha", "rope", "lora", "qlora", "speculative",
    "吞吐", "延迟", "显存", "内存墙", "带宽", "校准集", "minmax",
    "kl", "percentile", "entropy", "fakequant", "ste", "per-channel",
    "per-tensor", "w4a16", "w4a8", "int4", "fp8", "bf16", "npu",
    "昇腾", "hexagon", "snpe", "openvino", "mlir", "tvm", "xla",
    "delegate", "runtime", "调度", "图优化", "融合", "剪枝",
    "perplexity", "余弦", "对齐", "ota", "指纹", "验签", "车规",
    "vlm", "visual token", "chat template", "tokenizer",
    "精度位宽", "位宽", "对称", "非对称", "校准方法", "动态shape",
    "算子", "转换链路", "引擎选型", "kv", "paged",
}


def strip_num(title: str) -> str:
    return NUM_PREFIX.sub("", (title or "").strip()).strip()


def clamp(s: str, lo: int, hi: int) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    if len(s) <= hi:
        return s
    # cut at punctuation if possible
    cut = s[: hi - 1]
    for sep in ("。", "；", "，", "、", " "):
        i = cut.rfind(sep)
        if i >= lo - 5:
            return cut[: i + (1 if sep in "。；" else 0)] + ("…" if sep not in "。；" else "")
    return cut + "…"


def child_themes(node: dict, limit: int = 6) -> str:
    titles = [strip_num(c.get("t") or "") for c in (node.get("kids") or [])]
    titles = [t for t in titles if t]
    if not titles:
        return "若干子要点"
    shown = titles[:limit]
    more = "等" if len(titles) > limit else ""
    return "、".join(shown) + more


def score_k(title: str, desc: str = "", level: int = 3) -> int:
    """Heuristic importance: 2=core, 1=important, 0=normal. Prefer title hits."""
    t_low = strip_num(title).lower()
    d_low = (desc or "").lower()

    # Core only when the TITLE itself is the concept (not buried in long prose)
    core_title = (
        "kv cache", "kv-cache", "kv缓存", "transformer", "self-attention",
        "multi-head attention", "多头注意力", "prefill", "decode", "ttft",
        "onnx", "tensorrt", "qnn", "算子融合", "知识蒸馏", "zero-point",
        "zero point", "zeropoint",
    )
    for p in core_title:
        if p in t_low:
            return 2
    # short exact-ish titles
    exact_core = {
        "attention", "注意力", "量化", "校准", "门禁", "int8", "fp16",
        "scale", "蒸馏", "kv", "精度位宽", "scale 与 zero-point",
        "对称 vs 非对称", "ptq", "qat",
    }
    # title equals or starts with core token (avoid "尺子周" etc.)
    bare = re.sub(r"[（(].*?[）)]", "", t_low).strip()
    for tok in exact_core:
        if bare == tok or bare.startswith(tok + " ") or bare.startswith(tok + "与") or bare.startswith(tok + "/"):
            return 2
        if len(bare) <= 12 and tok in bare and tok in ("int8", "fp16", "onnx", "ttft", "prefill", "decode"):
            return 2

    # Important: title keywords only (desc-only marks are too noisy)
    for tok in K1_TOKENS:
        if tok.lower() in t_low:
            return 1
    if level == 2:
        hubs = ("主链路", "量化基础", "transformer", "门禁", "模型转换", "推理引擎", "kv")
        if any(h in t_low for h in hubs):
            return 1
    return 0


def expand_l3_d(title: str, old_d: str, l2: str, l1: str) -> str:
    """Turn shallow bullets into spoken 「是什么」prose."""
    t = strip_num(title)
    old = (old_d or "").strip()
    old_clean = re.sub(r"[🃏↪⏱↔⏩⚠✅*`]", "", old)
    old_clean = re.sub(r"\s+", " ", old_clean).strip()
    # idempotent: strip prior enrich wrappers
    m = re.match(rf"^「{re.escape(t)}」(?:指的是：|是「[^」]+」里要掌握的一点：)", old_clean)
    if m:
        old_clean = old_clean[m.end() :].strip()
        old_clean = re.sub(r"放到「[^」]+」整章语境里看，.*$", "", old_clean).strip(" 。")
    if old_clean.startswith(f"{t}：") and "它挂在" in old_clean:
        # previous template form
        old_clean = ""

    # Prefer concept templates when title hits a known idea (even if old_d exists)
    ctx = f"它挂在「{l1}」下的「{l2}」里"
    templates = []

    def hit(*keys: str) -> bool:
        # Title-only: avoid short titles matching keywords buried in old_d (e.g. 尺子周 + TTFT)
        tl = t.lower()
        return any(k.lower() in tl for k in keys)

    # stash old_clean for fallback after templates
    _old_for_fallback = old_clean
    _use_old_first = (
        len(old_clean) >= 48
        and not old_clean.startswith(("见原", "〇", "①", "②"))
        and not hit(
            "kv cache", "kv-cache", "kv缓存", "prefill", "decode", "ttft",
            "attention", "注意力", "transformer", "onnx", "tensorrt", "qnn",
            "量化", "scale", "零点", "zero-point", "精度位宽", "位宽",
            "校准", "ptq", "qat", "算子融合", "蒸馏", "门禁",
        )
    )
    if _use_old_first:
        lead = f"「{t}」指的是："
        body = old_clean
        if body.startswith(t):
            body = body[len(t) :].lstrip(" —–:：")
        prose = f"{lead}{body}"
        if not prose.endswith(("。", "；", "…", "！", "?")):
            prose += "。"
        return clamp(prose, 80, 180)

    if hit("kv cache", "kv-cache", "kv缓存") or (hit("kv") and "prefill" not in t.lower() and "decode" not in t.lower()):
        label = "KV Cache" if "kv" in t.lower() else t
        templates.append(
            f"{label}：生成时把已算过的 Key/Value 存起来复用，Decode 就不用整段重算 Attention。"
            f"{ctx}，后面谈 TTFT/吞吐时会反复用到它。"
        )
    elif hit("prefill"):
        templates.append(
            f"Prefill：用户提示整段一次性进模型、算出首段表示并填满 KV 的阶段；往往决定首字等多久出来。"
            f"（本点标题：{t}）{ctx}，和 Decode 对半拆延迟账。"
        )
    elif hit("decode"):
        templates.append(
            f"Decode：一个接一个吐 token 的阶段，每步主要吃 KV Cache 与带宽；端侧体感「慢不慢」常栽在这里。"
            f"（本点标题：{t}）{ctx}。"
        )
    elif hit("ttft", "首字", "首 token"):
        templates.append(
            f"TTFT（首字延迟）：从发起请求到第一个可用 token 出现的等待；端侧体感里它和 Prefill、视觉编码强绑定。"
            f"（本点标题：{t}）{ctx}，是验收表上常见的硬指标。"
        )
    elif hit("attention", "注意力"):
        templates.append(
            f"Attention（注意力）：让每个位置按相关度去「看」其他位置信息的机制；Transformer 里算力与访存的大头之一。"
            f"（本点标题：{t}）{ctx}，后面会接到 KV、融合与硬件实现。"
        )
    elif hit("transformer"):
        templates.append(
            f"Transformer：用堆叠的自注意力+前馈块做序列建模的主干结构；端侧大模型几乎都绕不开它。"
            f"（本点标题：{t}）{ctx}，后面量化、编译、KV 都围绕这块图展开。"
        )
    elif hit("onnx"):
        templates.append(
            f"ONNX：一种跨框架的中间模型格式，常作「训练框架 → 推理引擎」的交接面；图对不对、算子齐不齐先在这里验。"
            f"（本点标题：{t}）{ctx}。"
        )
    elif hit("tensorrt"):
        templates.append(
            f"TensorRT：面向 NVIDIA GPU 的高性能推理栈，做图优化、精度策略与引擎构建；车上/工控 GPU 路径常点名它。"
            f"（本点标题：{t}）{ctx}。"
        )
    elif hit("qnn", "snpe", "hexagon"):
        templates.append(
            f"{t}：高通侧把模型搬到 Hexagon/NPU 的工具与运行时一环；手机/车机 Qualcomm 方案会反复遇到。"
            f"{ctx}。"
        )
    elif hit("量化") and not hit("评估", "精度"):
        templates.append(
            f"{t}：把权重/激活从高精度数压到更少比特（如 INT8），换内存与算力，但要守住精度验收。"
            f"{ctx}，后面会拆 scale、校准与 PTQ/QAT。"
        )
    elif hit("scale", "零点", "zero-point", "zero point"):
        templates.append(
            f"{t}：浮点与整数量之间的「尺子」参数——scale 管间距，zero-point 管零点对齐；量化对不对先看它们稳不稳。"
            f"{ctx}。"
        )
    elif hit("精度位宽", "位宽"):
        templates.append(
            f"{t}：用多少比特存一个数——FP16/INT8/INT4 等；位宽越低越省内存与带宽，但也越容易伤精度。"
            f"选哪一档要和芯片算子能力、业务验收一起定。{ctx}。"
        )
    elif hit("校准", "标定", "calibration"):
        templates.append(
            f"{t}：用一小撮代表数据估激活分布，好定 scale/阈值；校准集歪了，后面 PTQ 再精也难救。"
            f"{ctx}。"
        )
    elif hit("ptq"):
        templates.append(
            f"{t}：训练完再量化，不动（或少动）原权重训练流程；端侧赶工时最常用，但依赖校准与图是否可量化。"
            f"{ctx}。"
        )
    elif hit("qat", "fakequant"):
        templates.append(
            f"{t}：训练阶段就插入伪量化，让网络提前适应低比特；精度更好，但成本与工具链更重。"
            f"{ctx}。"
        )
    elif hit("算子融合", "融合"):
        templates.append(
            f"{t}：把相邻小算子并成一次 kernel，少写中间结果、少启动开销；编译器/引擎优化的常规招。"
            f"{ctx}。"
        )
    elif hit("蒸馏"):
        templates.append(
            f"{t}：用大模型「教」小模型学分布或中间特征，换更小体积仍够用的效果；常与量化、剪枝搭着用。"
            f"{ctx}。"
        )
    elif hit("门禁"):
        templates.append(
            f"{t}：量产前那道「不过就不许上车」的检查——精度、性能、指纹、安全等要一起过；演示绿不等于门禁绿。"
            f"{ctx}。"
        )
    elif hit("int8", "fp16", "int4", "fp8", "bf16"):
        templates.append(
            f"{t}：一种具体数值精度/位宽选择；选哪档直接决定内存、速度与精度三角怎么折中。"
            f"{ctx}，要和硬件原生能力对齐。"
        )
    elif hit("runtime", "运行时"):
        templates.append(
            f"{t}：板上真正加载引擎、申请内存、喂输入出输出的那一层；转换成功不等于 Runtime 调度也成功。"
            f"{ctx}。"
        )
    elif hit("转换", "export", "导出"):
        templates.append(
            f"{t}：把训练态权重变成推理态图/格式的步骤；断点常出在算子不支持、动态 shape、自定义层。"
            f"{ctx}。"
        )
    else:
        # generic teaching wrapper
        if old_clean and len(old_clean) >= 12:
            templates.append(
                f"「{t}」是「{l2}」里要掌握的一点：{old_clean}。"
                f"放到「{l1}」整章语境里看，它帮你把概念落到可执行细节。"
            )
        else:
            templates.append(
                f"「{t}」是「{l2}」主题下的具体知识点（隶属「{l1}」）。"
                f"先抓住它在链路里站哪一站，再对照子笔记或原文档补命令与公式，避免只背名词。"
            )

    prose = templates[0]
    if not prose.endswith(("。", "；", "…")):
        prose += "。"
    return clamp(prose, 80, 180)


def make_l3_w(title: str, l2: str) -> str:
    t = strip_num(title)
    blob = t.lower()
    rules = [
        (("prefill",), "卡住首包/首字时间，是 TTFT 账单的前半段。"),
        (("decode",), "决定连续生成是否跟得上交互，和带宽/KV 强相关。"),
        (("ttft", "首字"), "交付验收的体感硬指标，用来卡「能不能开聊」。"),
        (("kv", "cache"), "决定 Decode 能否复用历史状态，直接影响吞吐与显存/内存占用。"),
        (("量化", "int8", "int4", "ptq", "qat", "位宽"), "让模型塞进端侧预算，是体积与算力交换精度的主手段。"),
        (("校准", "scale", "zero", "零点"), "把量化尺子定准，避免「压瘦了但答非所问」。"),
        (("onnx", "转换"), "保证训练成果能交到推理引擎，是主链路第一道闸。"),
        (("tensorrt", "qnn", "runtime", "引擎"), "把图画成板上可跑的高效执行，关乎真实延迟。"),
        (("融合", "编译", "算子"), "削掉多余访存与启动开销，常是性能优化的杠杆。"),
        (("门禁", "ota", "指纹", "验签"), "把「能演示」抬成「能量产」，挡住回滚与安全风险。"),
        (("蒸馏", "剪枝"), "在精度可接受前提下继续减负，和服务端同款大模型打配合。"),
        (("attention", "transformer"), "理解算力与内存从哪来，后续优化才有靶心。"),
    ]
    for keys, sent in rules:
        if any(k in blob for k in keys):
            return clamp(sent, 40, 100)
    return clamp(f"支撑「{l2}」落地：弄清它，排障与选型时才有抓手。", 40, 100)


def make_l3_b(title: str, l2: str, l1: str, siblings: list[str]) -> str:
    t = strip_num(title)
    nxt = ""
    if siblings:
        try:
            i = siblings.index(t)
            if i + 1 < len(siblings):
                nxt = f"下一看「{siblings[i+1]}」。"
            else:
                nxt = f"本主题叶子收尾，可回到「{l2}」总览或进入同章下一主题。"
        except ValueError:
            nxt = f"放在「{l2}」线索里对照前后点。"
    else:
        nxt = f"随后在「{l2}」内继续展开。"
    return clamp(f"上承「{l1} → {l2}」，点明「{t}」在该主题中的位置。{nxt}", 40, 120)


def make_l2_d(title: str, l1: str, themes: str) -> str:
    t = strip_num(title)
    return clamp(
        f"「{t}」是「{l1}」这一章里的主题块：先建立该块在端侧部署链路中的位置，再下钻子点。"
        f"本块主要覆盖：{themes}。"
        f"读法建议是「先看它管哪一段，再记名词」，避免把目录当知识。",
        80,
        180,
    )


def make_l2_w(title: str, l1: str) -> str:
    t = strip_num(title)
    return clamp(
        f"把「{l1}」拆成可讲、可练的一块，让后续术语/命令有归属，避免整章一锅粥。",
        40,
        100,
    )


def make_l2_b(title: str, l1: str, prev_l2: str | None, next_l2: str | None) -> str:
    t = strip_num(title)
    prev = f"上接「{prev_l2}」" if prev_l2 else f"承接章首「{l1}」"
    nxt = f"下启「{next_l2}」" if next_l2 else "之后进入同章下一主题或下一章"
    return clamp(f"{prev}，本主题「{t}」负责把该段讲透；{nxt}。", 40, 120)


def enrich(tree: dict) -> dict:
    tree["d"] = (
        "讲课序号 1→N（章=1 ·，主题=1.1，术语=1.1.1）。"
        "点开节点看「是什么 / 作用 / 承接」；高亮节点是重点概念（琥珀=重要，珊瑚=核心）。"
    )

    for c1 in tree.get("kids") or []:
        l1 = strip_num(c1.get("t") or "")
        # lightly enrich L1 d if empty/short
        if len((c1.get("d") or "").strip()) < 40:
            themes = child_themes(c1, 5)
            c1["d"] = clamp(
                f"「{l1}」这一章回答端侧部署里一块完整问题。下含主题：{themes}。"
                f"先建立章目标，再进 1.x 主题与术语，避免跳着背命令。",
                80,
                180,
            )
        if "w" not in c1 or not c1.get("w"):
            c1["w"] = clamp(f"给后续主题提供章节锚点，保证学习与排障按链路推进。", 40, 100)
        if "b" not in c1 or not c1.get("b"):
            c1["b"] = clamp(f"承上启下：从总览进入「{l1}」，再下钻主题与术语。", 40, 120)
        c1["k"] = score_k(l1, c1.get("d") or "", level=1)
        # L1 rarely coral
        if c1["k"] == 2:
            c1["k"] = 1

        l2_nodes = c1.get("kids") or []
        l2_titles = [strip_num(s.get("t") or "") for s in l2_nodes]

        for j, c2 in enumerate(l2_nodes):
            l2 = strip_num(c2.get("t") or "")
            themes = child_themes(c2, 6)
            # Always synthesize L2 teaching prose from title + child themes
            c2["d"] = make_l2_d(l2, l1, themes)

            c2["w"] = make_l2_w(l2, l1)
            prev = l2_titles[j - 1] if j > 0 else None
            nxt = l2_titles[j + 1] if j + 1 < len(l2_titles) else None
            c2["b"] = make_l2_b(l2, l1, prev, nxt)
            c2["k"] = score_k(l2, c2.get("d") or "", level=2)

            sibs = [strip_num(x.get("t") or "") for x in (c2.get("kids") or [])]
            for c3 in c2.get("kids") or []:
                t3 = strip_num(c3.get("t") or "")
                c3["d"] = expand_l3_d(t3, c3.get("d") or "", l2, l1)
                c3["w"] = make_l3_w(t3, l2)
                c3["b"] = make_l3_b(t3, l2, l1, sibs)
                c3["k"] = score_k(t3, c3.get("d") or "", level=3)

    # second pass: tune leaf highlight density ~15–22%; k=2 should stay minority
    leaves = []
    for c1 in tree.get("kids") or []:
        for c2 in c1.get("kids") or []:
            for c3 in c2.get("kids") or []:
                leaves.append(c3)
    marked = [n for n in leaves if n.get("k", 0) > 0]
    target_hi = max(1, int(len(leaves) * 0.22))
    target_lo = int(len(leaves) * 0.14)
    # demote excess k=2 → k=1 if coral too dense
    k2s = [n for n in leaves if n.get("k") == 2]
    k2_cap = max(20, int(len(leaves) * 0.08))
    if len(k2s) > k2_cap:
        k2s.sort(key=lambda n: (-len(strip_num(n.get("t") or "")), n.get("id") or ""))
        for n in k2s[k2_cap:]:
            n["k"] = 1
    marked = [n for n in leaves if n.get("k", 0) > 0]
    if len(marked) > target_hi:
        ones = [n for n in marked if n.get("k") == 1]
        ones.sort(key=lambda n: (-len(strip_num(n.get("t") or "")), n.get("id") or ""))
        need = len(marked) - target_hi
        for n in ones[:need]:
            n["k"] = 0
    elif len(marked) < target_lo:
        zeros = [n for n in leaves if n.get("k", 0) == 0]
        boost_keys = (
            "onnx", "tensorrt", "attention", "prefill", "decode", "int8",
            "fp16", "校准", "scale", "runtime", "gguf", "ptq", "qat", "kv",
        )
        for n in zeros:
            t = strip_num(n.get("t") or "").lower()
            if any(k in t for k in boost_keys):
                n["k"] = 1
            if sum(1 for x in leaves if x.get("k", 0) > 0) >= target_lo:
                break

    # L2 key density: keep fewer
    l2s = [c2 for c1 in tree.get("kids") or [] for c2 in (c1.get("kids") or [])]
    l2_marked = [n for n in l2s if n.get("k", 0) > 0]
    l2_cap = max(8, int(len(l2s) * 0.15))
    if len(l2_marked) > l2_cap:
        ones = [n for n in l2_marked if n.get("k") == 1]
        ones.sort(key=lambda n: (-len(strip_num(n.get("t") or "")), n.get("id") or ""))
        # also demote long-title k=2 at L2
        twos = [n for n in l2_marked if n.get("k") == 2]
        twos.sort(key=lambda n: (-len(strip_num(n.get("t") or "")), n.get("id") or ""))
        for n in twos:
            if len(l2_marked) <= l2_cap:
                break
            n["k"] = 1
            l2_marked = [x for x in l2s if x.get("k", 0) > 0]
        hub_keep = ("量化基础", "模型转换", "推理引擎", "主链路", "门禁", "transformer", "kv")
        for n in ones:
            if len([x for x in l2s if x.get("k", 0) > 0]) <= l2_cap:
                break
            t = strip_num(n.get("t") or "").lower()
            if any(h in t for h in hub_keep):
                continue
            n["k"] = 0

    return tree


def inject(path: Path, payload: str) -> None:
    """Replace const TREE = {...}; using brace-aware scan (regex .*? breaks on nested })."""
    html = path.read_text(encoding="utf-8")
    start = html.find("const TREE = ")
    if start < 0:
        raise SystemExit(f"inject failed for {path.name}: const TREE not found")
    eq = html.find("=", start)
    i = eq + 1
    while i < len(html) and html[i] in " \n\r\t":
        i += 1
    if i >= len(html) or html[i] != "{":
        raise SystemExit(f"inject failed for {path.name}: expected {{")
    depth = 0
    in_str = False
    esc = False
    j = i
    while j < len(html):
        ch = html[j]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
        j += 1
    k = j
    while k < len(html) and html[k] in " \t":
        k += 1
    if k < len(html) and html[k] == ";":
        k += 1
    new_html = html[:start] + "const TREE = " + payload + ";" + html[k:]
    # verify parseable
    i2 = new_html.find("const TREE = ") + len("const TREE = ")
    while new_html[i2] in " \n\r\t":
        i2 += 1
    json.JSONDecoder().raw_decode(new_html, i2)
    path.write_text(new_html, encoding="utf-8")
    print("injected", path.name, path.stat().st_size)


def stats(tree: dict) -> None:
    filled_d = filled_w = filled_b = k1 = k2 = 0
    l2_samples, l3_samples = [], []
    for c1 in tree.get("kids") or []:
        for fld in ("d", "w", "b"):
            if (c1.get(fld) or "").strip():
                if fld == "d":
                    filled_d += 1
                elif fld == "w":
                    filled_w += 1
                else:
                    filled_b += 1
        if c1.get("k") == 1:
            k1 += 1
        elif c1.get("k") == 2:
            k2 += 1
        for c2 in c1.get("kids") or []:
            if (c2.get("d") or "").strip():
                filled_d += 1
            if (c2.get("w") or "").strip():
                filled_w += 1
            if (c2.get("b") or "").strip():
                filled_b += 1
            if c2.get("k") == 1:
                k1 += 1
            elif c2.get("k") == 2:
                k2 += 1
            if len(l2_samples) < 3:
                l2_samples.append(c2)
            for c3 in c2.get("kids") or []:
                if (c3.get("d") or "").strip():
                    filled_d += 1
                if (c3.get("w") or "").strip():
                    filled_w += 1
                if (c3.get("b") or "").strip():
                    filled_b += 1
                if c3.get("k") == 1:
                    k1 += 1
                elif c3.get("k") == 2:
                    k2 += 1
                if len(l3_samples) < 3:
                    l3_samples.append(c3)

    n_l2 = sum(len(c.get("kids") or []) for c in tree.get("kids") or [])
    n_l3 = sum(
        len(s.get("kids") or [])
        for c in tree.get("kids") or []
        for s in (c.get("kids") or [])
    )
    print("=== enrich stats ===")
    print(f"L1={len(tree.get('kids') or [])} L2={n_l2} L3={n_l3}")
    print(f"filled d={filled_d} w={filled_w} b={filled_b}")
    print(f"k=1 → {k1}  k=2 → {k2}  (leaf k>0 ≈ {sum(1 for c in tree['kids'] for s in c.get('kids') or [] for x in s.get('kids') or [] if x.get('k',0)>0)}/{n_l3})")
    print("--- sample L2 ---")
    for n in l2_samples:
        print(json.dumps({k: n.get(k) for k in ("id", "t", "d", "w", "b", "k")}, ensure_ascii=False, indent=2))
    print("--- sample L3 ---")
    for n in l3_samples:
        print(json.dumps({k: n.get(k) for k in ("id", "t", "d", "w", "b", "k", "kids")}, ensure_ascii=False, indent=2))


def main() -> None:
    tree = json.loads(TREE_JSON.read_text(encoding="utf-8"))
    tree = enrich(tree)
    payload = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
    TREE_JSON.write_text(payload, encoding="utf-8")
    print("wrote", TREE_JSON, "bytes", len(payload.encode("utf-8")))
    inject(HTML, payload)
    stats(tree)


if __name__ == "__main__":
    main()
