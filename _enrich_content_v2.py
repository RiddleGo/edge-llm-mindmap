# -*- coding: utf-8 -*-
"""Enrich mindmap content: keep 承上启下 only on L1/L2; deepen L3 是什么/作用."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
TREE_JSON = ROOT / "mindmap-tree.json"
HTMLS = [
    ROOT / "端侧部署思维导图.html",
    ROOT / "index.html",
]

NUM = re.compile(r"^\d+(?:\.\d+)*\s*[·.\s、\-–—]+\s*")

# concept-specific teaching blurbs keyed by substring in stripped title
CONCEPTS: list[tuple[tuple[str, ...], str, str]] = [
    (("端侧", "on-device", "设备本体"),
     "数据产生/消费处的终端或嵌入式节点上的推理：权重进本机 DRAM，默认不依赖跨城回程。杀进程、温控、前台保活都是硬约束。本仓库「端侧」专指这一层，勿与近边/MEC 混称。",
     "认清落点才能选验收尺：端侧看本机峰值与离线，不看云端 Demo 延迟。"),
    (("近边", "mec", "access-edge"),
     "接入网边缘的虚拟化宿主（MEC host）：基站旁/园区 PoP 上的算力与编排。时延与主权跟运营商/园区域走，不是手机里的 NPU。",
     "部署图要把近边与端侧分开画：RTT、编排主权、失败回落写清，才不会把 MEC 当手机。"),
    (("信任边界",),
     "谁持钥、谁编排、谁审计、故障归谁。物理共址不等于同一信任域：MEC 与 Edge Cloud 可同机房不同域。",
     "评审翻车常因 PPT 只画「边缘」说不清主权；部署图建议画三列——算力归属/数据驻留/编排主权。"),
    (("访存墙", "带宽墙", "memory-bound"),
     "端侧 LLM decode 多为 batch≈1：每 token 重读常驻权重与 KV，算术强度极低，瓶颈在搬字节而非宣传 TOPS。",
     "对话跟手先问有效带宽与 bytes/token，再谈 NPU TOPS；Prefill 与 Decode 必须分表。"),
    (("数据最小化",),
     "只处理目的所必要的数据：少采、少存、少传、少副本。端侧减少外传是手段之一，不等于自动合规。",
     "数据流图要标原始/特征/日志/遥测四级；「本地模型」挡不住全量日志回传的拒收。"),
    (("能加载", "容量门"),
     "四级台阶第一道：权重进设备、能出首帧，且峰值内存低于可用 DRAM。格式对 ≠ 能交付。",
     "OOM 比慢更致命；装不进就不要往下谈量化与加速。"),
    (("能量化", "塞入"),
     "四级台阶第二道：INT4/W4A16 等路径跑通，体积进预算，业务掉点与速度同表验收。",
     "塞进去但不能用等于没交付；无校准指纹的量化包当场拒收。"),
    (("可复现", "指纹门"),
     "四级台阶第三道：同一 SoC/引擎版本/导出指纹下，转换→Runtime→Profiling 可复跑，算子落点可审计。",
     "演示 APK 与「我机器上可以」过不了量产；静默 CPU fallback 不算加速。"),
    (("交付门禁",),
     "四级台阶第四道：共板、温区 sustained、OTA 可回滚、崩溃/OOM 率可追溯。演示绿 ≠ 门禁绿。",
     "空调房峰值挡不住座舱投诉；验收看 P95 与热稳态。"),
    (("精度位宽", "位宽"),
     "用多少比特存一个数：FP16 / INT8 / INT4 等。位宽越低越省内存和带宽，精度也更容易掉。选档要对齐芯片原生算子和业务验收线，别只看体积。",
     "这是端侧「塞不塞得下」的第一扳手：位宽定了，后面的 scale、校准、性能账才有意义。"),
    (("scale", "zero-point", "zero point", "zeropoint"),
     "浮点和整数之间的映射参数：scale 管「一格代表多大」，zero-point 管「零点落在哪」。量化对不对，先看这两把尺子稳不稳、有没有通道间乱飘。",
     "尺子歪了，后面 PTQ/QAT 再精也像在歪尺子上雕花——排障优先核对 scale/zp。"),
    (("对称", "非对称"),
     "对称量化以 0 为中心、正负共用一套 scale；非对称带 zero-point，更能贴合一边偏的激活分布。实现复杂度和硬件支持不一样。",
     "激活分布偏不偏，决定你能不能省掉 zp、能不能吃到更快的对称 kernel。"),
    (("量化粒度", "per-tensor", "per-channel"),
     "一组数共享一套量化参数的范围：整张张量一份（per-tensor）还是每个通道一份（per-channel）。粒度越细通常越准，也更吃存储与算子支持。",
     "精度掉点时先问粒度够不够细，再问校准集；很多「INT8 崩了」其实是 per-tensor 扛不住通道差异。"),
    (("量化公式", "量化映射"),
     "典型形式：实数 ≈ scale × (整数量 − zero-point)。正向量化、反向量化、饱和裁剪都围着这条式子转。",
     "公式是共同语言：和工具链、日志、论文对齐时，先把 scale/zp 定义说清楚再比数值。"),
    (("校准", "标定", "calibration"),
     "用一小撮代表数据估激活分布，从而定 scale/阈值。校准集不代表线上分布，后面再精的 PTQ 也救不回来。",
     "PTQ 成败大半看校准：集子要覆盖主路径场景，别用「随手抽的几张图」糊弄。"),
    (("校准集",),
     "专门用来估分布的小数据集。要覆盖主业务输入，避免只含简单样本导致 scale 偏乐观。",
     "校准集选错，表现为「离线指标还行、上线一碰就糊」——先查集子再查算法。"),
    (("误差来源", "clip", "round"),
     "量化误差常见三块：裁剪（clip）砍掉长尾、舍入（round）丢小数、权重/激活分布不对称导致同一套参数顾此失彼。",
     "掉点时按这三类拆账，比盲目换算法快：先看是不是 clip 太狠，再看 round 与粒度。"),
    (("ptq", "后训练"),
     "训练结束后再量化，基本不动原训练流程。上线快，但对校准和可量化图结构敏感。",
     "端侧赶工默认先 PTQ；精度不够再考虑 QAT 或混合精度，别一上来就重训。"),
    (("qat", "感知训练", "fakequant"),
     "训练时插入伪量化，让网络提前适应低比特。精度通常更好，成本和工具链更重。",
     "当 PTQ 卡在验收线以下、又有训练资源时再上；它不是免费午餐。"),
    (("kv cache", "kv-cache", "kv缓存"),
     "生成时把已算过的 Key/Value 存起来复用，Decode 就不用整段重算 Attention。省算力，但占内存，长度一长就胀。",
     "端侧长对话的内存墙多半在这：优化吞吐前先算清 KV 占多少。"),
    (("prefill",),
     "提示词整段一次性进模型、算出首段表示并填满 KV 的阶段。往往决定首字等多久出来，算力更密。",
     "TTFT 差，先看 Prefill：序列长、视觉编码、是否多余重算。"),
    (("decode",),
     "一个接一个吐 token 的阶段，每步主要吃 KV 与带宽。体感「生成慢不慢」常栽在这里。",
     "交互跟手度看 Decode；带宽和 KV 布局比盲目加核数更管用。"),
    (("ttft", "首字", "首token"),
     "从发请求到第一个可用 token 出现的等待。端侧体感里它和 Prefill、视觉编码强绑定，常是验收硬指标。",
     "产品说「慢」，先拆成 TTFT 还是 Decode；两者治法完全不同。"),
    (("attention", "注意力"),
     "按相关度决定每个位置「看」哪些位置的信息。Transformer 里算力与访存大头之一，后面的融合、KV、量化都围着它转。",
     "性能热点图若扎在 Attention，下一步才是融合、量化或改 GQA/MQA。"),
    (("transformer",),
     "堆叠自注意力 + 前馈块做序列建模的主干。端侧大模型几乎都绕不开它。",
     "后面量化、编译、KV、算子支持，默认都假设图是 Transformer 族。"),
    (("onnx",),
     "跨框架中间格式，常作训练框架到推理引擎的交接面。图对不对、算子齐不齐，先在这里验。",
     "转换失败优先查 ONNX：动态 shape、自定义算子、opset 版本。"),
    (("tensorrt",),
     "NVIDIA 推理引擎：解析 ONNX/自定义网络，做层融合、精度校准与 engine 序列化；版本必须对齐驱动与目标 GPU。",
     "先锁定 TRT 大版本与芯片，再谈 plugin、INT8/FP8 与 engine 缓存是否可复用。"),
    (("qnn", "snpe", "hexagon"),
     "高通侧把模型搬到 Hexagon/NPU 的工具与运行时一环。手机/车机 Qualcomm 方案会反复遇到。",
     "高通板上「能转不能跑」多半卡在 DSP/NPU 算子覆盖与上下文配置。"),
    (("算子融合", "融合"),
     "把相邻小算子并成一次 kernel，少写中间结果、少启动开销。编译器/引擎优化的常规招。",
     "Profiling 见一串碎算子，优先问能不能融合，再谈换精度。"),
    (("蒸馏",),
     "用大模型教小模型学分布或中间特征，换更小体积仍够用的效果。常与量化、剪枝搭着用。",
     "体积还差一截、精度又不能再砍时，蒸馏是「换结构」而不是「换比特」。"),
    (("门禁", "ota", "指纹", "验签"),
     "量产前「不过就不许上车」的检查：精度、性能、指纹、安全等要一起过。演示绿不等于门禁绿。",
     "交付周看门禁矩阵，不看单机 demo；少一项都会在 OTA/回滚里爆。"),
]


def strip_num(title: str) -> str:
    return NUM.sub("", (title or "").strip()).strip()


def clamp(s: str, lo: int, hi: int) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    if len(s) <= hi:
        return s if len(s) >= lo or not s else s
    cut = s[: hi - 1]
    for sep in ("。", "；", "，", "、", " "):
        i = cut.rfind(sep)
        if i >= lo - 5:
            return cut[: i + (1 if sep in "。；" else 0)] + ("…" if sep not in "。；" else "")
    return cut + "…"


def unwrap_template(title: str, d: str) -> str:
    t = strip_num(title)
    d = (d or "").strip()
    d = re.sub(r"[🃏↪⏱↔⏩⚠✅*`]", "", d)
    d = re.sub(r"\s+", " ", d).strip()
    # strip common wrappers
    patterns = [
        rf"^「{re.escape(t)}」是「[^」]+」里要掌握的一点：",
        rf"^「{re.escape(t)}」指的是：",
        rf"^{re.escape(t)}：",
        rf"^「{re.escape(t)}」是「[^」]+」这一章里的主题块：先建立该块在端侧部署链路中的位置，再下钻子点。",
    ]
    for p in patterns:
        d = re.sub(p, "", d).strip()
    d = re.sub(r"放到「[^」]+」整章语境里看，.*$", "", d).strip(" 。")
    d = re.sub(r"它挂在「[^」]+」下的「[^」]+」里。?$", "", d).strip(" 。")
    d = re.sub(r"本块主要覆盖：.*$", "", d).strip(" 。")
    d = re.sub(r"读法建议是.*$", "", d).strip(" 。")
    d = re.sub(r"先建立该块在端侧部署链路中的位置，再下钻子点。?", "", d).strip(" 。")
    return d


def match_concept(title: str) -> tuple[str, str] | None:
    tl = strip_num(title).lower()
    # Prefer longest key hit so "端 · 近边 · 云" does not steal the short "近边" gloss
    best: tuple[str, str] | None = None
    best_len = -1
    for keys, d, w in CONCEPTS:
        for k in keys:
            kl = k.lower()
            if kl in tl and len(kl) > best_len:
                best = (d, w)
                best_len = len(kl)
    # Compound layer title: keep prose, not a single-layer gloss
    if "端" in tl and "近边" in tl and "云" in tl:
        return None
    return best


def _hit(text: str, *keys: str) -> bool:
    tl = (text or "").lower()
    return any(k.lower() in tl for k in keys)


def idea_clip(title: str, lo: int = 8, hi: int = 14) -> str:
    """Short conceptual stub from a title — never the full catalog string."""
    s = strip_num(title or "")
    s = re.split(r"[：:、（(\|]", s, maxsplit=1)[0].strip()
    s = re.sub(r"\s+", " ", s)
    if len(s) > hi:
        s = s[:hi].rstrip(" ·-–—/")
    if len(s) < min(lo, 4):
        raw = strip_num(title or "")
        s = raw[:hi].rstrip(" ·-–—/") if raw else ""
    return s


def conceptual_bridge(
    t: str,
    prev: str | None,
    nxt: str | None,
    l1_title: str,
    kids_themes: list[str],
) -> str:
    """Spoken pipeline logic for L1/L2 `b`. Titles are hints only — never dumped."""
    t = strip_num(t or "")
    prev = strip_num(prev or "") if prev else ""
    nxt = strip_num(nxt or "") if nxt else ""
    l1 = strip_num(l1_title or "")
    kids = " ".join(kids_themes or [])

    def T(*keys: str) -> bool:
        return _hit(t, *keys)

    def P(*keys: str) -> bool:
        return _hit(prev, *keys)

    def N(*keys: str) -> bool:
        return _hit(nxt, *keys)

    # L1 调用时 l1_title 为空；避免章名误撞主题关键词（如「昇腾」）
    if not l1:
        if T("先认端侧"):
            return "进技术命令之前先认方位：端相对近边/云站哪一层、为啥挤上设备、访存墙、四级台阶、场景拒收尺、交哪种活。方位清了，全栈入门才不是工具堆。"
        if T("基础入门") or T("全栈技术"):
            return "方位认完，用一条可跑的全栈把转换、量化、CV/昇腾/LLM 摸一遍。主链路章再把其中转换、引擎、运行时拆开深讲。"
        if T("部署主链路"):
            return "全栈走过，把部署收成转换→引擎编译→运行时三截。这三截通了，才回头补模型和硬件底座，量化才有图可压。"
        if T("前置底座"):
            return "主链路默认你会模型、编译、硬件。这段把三块底座补齐，量化章才有物理和数学上限，不会把位宽当软件开关。"
        if T("量化与压缩"):
            return "底座齐了才动比特。先立量化尺子，再 PTQ/QAT/低比特，最后用精度评估和轻量化收口，附录才摊公式。"
        if T("量化数学") or T("校准细则"):
            return "量化流程章讲怎么做，附录把公式、粒度、校准数学摊开。数学清了，性能优化才不会在糊模型上抠时延。"
        if T("推理性能优化") and not T("方法论"):
            return "精度过线才谈快。先定位瓶颈，再融合、KV、带宽、Decode，最后才下 kernel；附录再把命令和平台开关补齐。"
        if T("性能命令") or T("平台开关"):
            return "性能方法论有了，附录给出命令、GGUF、TRT-LLM、板上开关。把「快」落成可复现实验，编译器章才能接着讲图为什么被编成那样。"
        if T("算子工程") or (T("AI 编译器") and not T("栈") and not T("核心算子实现")):
            return "引擎好用还要懂图怎么被编译、算子为啥匹配失败。这段给后续平台工具链共同语言，避免只会贴厂商教程。"
        if T("平台工具链扩展"):
            return "编译器和主干懂了，按厂商把 QNN/TRT/昇腾/跨平台对照铺开。对照清楚，昇腾/麒麟实战才不是第一家宣传页。"
        if T("平台工具链") and not T("扩展"):
            return "编译器共性讲完，先落到高通 QNN 与英伟达 TensorRT 两条实链。两家都摸过，扩展章再铺其它 SoC 和对照表。"
        if T("LLM") and T("VLM") and T("补全"):
            return "工具链之外，把近年模型、RAG、VLM、门禁补进端侧清单。补全是为了教材不停留在旧量化，Transformer 章再把算子讲透。"
        if T("Transformer") and T("编译器"):
            return "补全章偏产品能力，这段把 Transformer/VLM 算子和编译器 IR 讲透。算子清了，平台工具链扩展才能按厂商对得上。"
        if T("昇腾") and T("麒麟"):
            return "工具链对照之后，用昇腾/麒麟板把 OMG、算子搜索、ADB 跑通。板子会跑，工程化章再谈量产，不把实验当交付。"
        if T("端侧工程化") or (T("量产落地") and not T("门禁")):
            return "板子会跑了，把 LLM/VLM 从训练到车机、QNN/TRT 迁移、车规约束串成量产路径。路径有了，再收流水线与门禁。"
        if T("工程化与量产"):
            return "量产路径走过，收成流水线、回归、资源评估和文档。附件齐了，门禁章才能写「不过就不许上车」。"
        if T("门禁") and T("OTA"):
            return "流水线能重复，才上门禁、车规、OTA 与安全。演示绿不等于放行绿，这是全书交付收口，不再开新的技术栈。"

    # ----- 连载 / 台阶 / 场景 / 认端侧新节 -----
    if T("连载顺序"):
        return "先把整本课排成可走的周次，不按编号硬闯。入门、主链路、尺子、平台、交付五周认清，才谈端/边/云边界与四级台阶。"
    if T("端 · 近边") or T("词钉死"):
        return "周次有了，先钉术语：端=设备本体，近边=MEC/接入网边缘，云=中心。词钉死，后面「为啥挤上设备」才不会把 MEC 当手机。"
    if T("信任边界"):
        return "三层名字钉死后，再分清信任域与机柜：共址≠可控。信任边界清了，协作切分才写得进部署图。"
    if T("协作面") or T("不是替代"):
        return "信任域分清后，端边云按任务切分，不是互相替代。切分表有了，才谈为啥要把推理挤上设备。"
    if T("边界决策四问"):
        return "协作原则有了，用四问做现场 checklist。问完再进动机章，避免口号式「上边缘」。"
    if T("为什么要把推理挤上设备"):
        return "三层边界清了，才谈动机：隐私、延迟、成本、离线。动机落到产业锚点，下一步先深挖时延与可用性。"
    if T("时延与可用性"):
        return "动机表看过，先深挖时延：本机测 TTFT/稳态，不抄云 Demo。时延账清了，再谈数据最小化。"
    if T("数据最小化"):
        return "时延约束之后谈隐私手段：少传少存。最小化是设计默认，不是「本地=合规」；再看产业产品线如何把模型挤上设备。"
    if T("可挤上设备") or T("做成产品线"):
        return "约束讲清后，看 Apple/Phi/Llama 把小模型做成可交付路径。选型表有了，才列「何时不要硬挤」。"
    if T("何时不要硬挤"):
        return "能挤的边界认清，再用拒收清单防止硬扛。收束后进访存墙——主矛盾往往在搬而不在算。"
    if T("访存墙：") or (T("访存墙") and T("主矛盾") and not T("是什么") and not T("怎么量") and not T("误判") and not T("锚点") and not T("为何")):
        return "何时不硬挤列完，总览访存墙：主矛盾在搬不在算。总览后先定义「是什么」，再拆为何/怎么量。"
    if T("访存墙是什么"):
        return "动机收束后，先定义访存墙：batch≈1 decode 每 token 扫权重。定义清了，才讲为何它是端侧主矛盾。"
    if T("为何访存是主矛盾"):
        return "定义有了：prefill 吃算力、decode 吃带宽。主矛盾钉死，下一步才谈怎么量，别再用 TOPS 代替 tok/s。"
    if T("访存墙怎么量"):
        return "主矛盾认清后立表计：算术强度、有效带宽、稳态 tok/s。量表齐了，再列常见误判当红黄牌。"
    if T("访存墙常见误判"):
        return "会量之后对照误判：TOPS≠对话快、能加载≠能交付。误判清了，再用带条件的锚点数字钉课堂。"
    if T("访存墙锚点") or (T("锚点") and T("条件写死")):
        return "误判清单之后给锚点：Phi/Orin/骁龙/Tiny，条件写死。锚点只认方位，过门细节进四级台阶。"
    if T("四级台阶"):
        return "访存墙提醒你演示≠交付。四级台阶把能力拆成可度量的门；过了哪道门，才谈手机/车机/盒子各用哪把拒收尺。"
    if T("L1") and T("能加载"):
        return "总表看过，先过容量门：装得进、不 OOM。L1 过了才谈量化塞入，否则后面全是空转。"
    if T("L2") and T("能量化"):
        return "能加载之后压 bit：体积与业务掉点同表验收。L2 过了才谈工具链指纹，别只交演示 APK。"
    if T("L3") and T("可复现"):
        return "量化过线后钉指纹：同脚本同版本可复跑。L3 过了才谈长稳与 OTA，演示机不算交付。"
    if T("L4") and T("交付门禁"):
        return "指纹齐了才上门禁：P95、热稳态、回滚。L4 过了再按场景选拒收尺，空调房绿表无效。"
    if T("落地场景"):
        return "台阶认完才谈现场：车上、手机、工控各用哪把拒收尺。场景清楚了，才立现场拒收尺，别把演示当交付。"
    if T("现场拒收尺"):
        return "场景定了才立尺：DRAM、TTFT、稳态 tok/s、掉点、温控。尺立住，三种活才知道各自交哪张表。"
    if T("表 A") or (T("DRAM 峰值") and T("模型体积")):
        return "五张拒收尺从内存开刀：OOM 比慢更致命。表 A 钉住，再测 TTFT，避免首字体验被内存抖动掩盖。"
    if T("表 B") or (T("TTFT") and T("Prefill") and T("测什么")):
        return "内存过线后测首字：TTFT/Prefill。首包合格，再验 decode 稳态，别用一个「最高 tok/s」糊弄。"
    if T("表 C") or (T("Decode") and T("稳态")):
        return "首字过后看持续生成与温区。稳态过了，再验量化掉点——快但胡话同样拒收。"
    if T("表 D") or (T("量化精度掉点") and T("测什么")):
        return "速度过线必须过精度：业务集与对齐三站。精度立住，最后才验功耗与温控掉速。"
    if T("表 E") or (T("功耗") and T("温控掉速") and T("测什么")):
        return "精度过线后验热与电：会话级功耗、结温–频率曲线。五表齐了，再分三种活各交哪张单。"
    if T("三种活", "职业"):
        return "拒收尺立住才分活：交到板上、变轻变快、Runtime/算子不是同一份工。职业切口立住，后面技术章才知道自己在交哪一截。"
    if T("出处速查"):
        return "方位、台阶、场景、拒收尺认完，用出处表回查标准与厂商锚点。数字进合同仍以板上 profiler 为准，然后进 ⑫ 动手。"

    # ----- CV / 昇腾 / llama.cpp / 引擎栈（用前后文选句） -----
    if T("CV") and T("ONNX", "INT8", "全链路", "PT"):
        return "三平台环境通了，先用 CV 把 PT→ONNX→INT8→精度验收走通。同一套量化图后面才换昇腾编译入口，别一上来就上大模型。"
    if T("昇腾") and T("DDK", "NPU部署", "OMC转换"):
        if P("CV", "ONNX", "INT8") or P("PT→") or P("精度评估"):
            return "CV 那条已经把 PT→ONNX→INT8→精度验收走通。昇腾要换成自家 OMC/DDK/OMG 和算子库：同样的量化图，换编译入口。跑通板子后才轮到 LLM 的 GGUF/KV，因为大模型还多一层缓存账。"
        if N("llama.cpp", "GGUF", "KV"):
            return "这块把图编进昇腾：OMC/DDK/OMG 和算子搜索知识库。板子跑通，下一步才是 LLM 的 GGUF 与 KV，不能把大模型当又一个 INT8 套件。"
        return "昇腾不复用通用 INT8 引擎入口，要走 OMC/DDK/OMG 和算子库。编译入口换对了，板上验收才有意义，再谈别的芯片栈。"
    if T("llama.cpp") or (T("GGUF") and T("KV", "LLM", "端侧部署")):
        if P("昇腾", "OMC"):
            return "昇腾把 CV 图编到板上了。LLM 换 llama.cpp/GGUF，还要单独算 KV 缓存，不能当又一个 INT8 模型套。生成跑通后再看车载引擎全景。"
        if T("GGUF") and not T("llama.cpp"):
            return "端侧 LLM 的权重封装多落在 GGUF/K-quant。格式选对了，llama.cpp 后端和 kernel 才接得上，否则量化档是空的。"
        return "LLM 端侧不是再跑一条 CV 量化。llama.cpp/GGUF 管权重，KV 管生成时内存；这两本账清了，才对照各家车载引擎。"
    if T("GGUF") or T("Q4_K", "K-quant"):
        return "精度-资源权衡有了，才落到 GGUF 档位。Q4_K_M 这类格式决定体积和掉点，下一步才是 llama.cpp 后端怎么把档跑起来。"
    if T("车载芯片") or (T("推理引擎") and T("全景", "技术栈")):
        return "LLM 的 GGUF/KV 账有了，才对照车载各家引擎栈。选型清楚再下钻编译器与算子，避免一上来绑死某一家宣传页。"

    # ----- 量化基础 / PTQ / QAT / 低比特 / 精度评估 / 轻量化 -----
    if T("量化基础") and not T("原理", "公式", "数学"):
        return "压缩这一章先立尺子：位宽、scale、粒度、对称与否。尺子没立，后面 PTQ 校准就是空转；PTQ 过线才值得上 QAT。"
    if T("后训练") or (T("PTQ") and not T("完整流程", "训练后量化完整")):
        if T("完整流程") or T("训练后量化完整"):
            return "校准方法齐了，把 PTQ 从头到尾串成可重复流程。流程不稳，QAT 的伪量化也无从对比，更别谈学习式 scale。"
        return "尺子立住了才做后训练量化：不动原训练、靠校准定 scale。PTQ 仍卡验收线，下一步才是 QAT 伪量化，别一上来重训。"
    if T("量化感知") or T("QAT") or T("FakeQuant") or T("STE"):
        if T("STE") or T("FakeQuant"):
            return "PTQ 流程跑通仍掉点，才上伪量化与 STE。QAT 会把尺子也卷进训练，后面 LSQ/PACT 才有地方接，低比特另算。"
        return "PTQ 走不通才插入伪量化重训。QAT 更准也更贵；过了 INT8 舒适区，低比特 INT4/GPTQ 还要另开一档验收。"
    if T("低比特") or T("INT4") or T("GPTQ") or T("AWQ"):
        if T("Weight-only") or T("Hessian"):
            return "激活难量化就先只压权重。GPTQ 用 Hessian 补偿低比特误差，收口必须用任务指标，不能只看权重 MSE。"
        return "QAT 还多在 INT8 舒适区。INT4/GPTQ/AWQ 是再砍一档，体积账和精度账要一起看，下一步用评估尺子收口，别只报压缩比。"
    if T("精度评估") or T("余弦") or T("Perplexity") or T("MMLU"):
        if T("LLM") or T("Perplexity") or T("MMLU"):
            return "CV 的 top-1 看不准生成质量。PPL/MMLU 才是 LLM 量化验收；过了这层，蒸馏剪枝协同才有资格上，否则在糊输出上继续压。"
        if P("INT4", "GPTQ", "低比特", "AWQ"):
            return "低比特有没有掉点，要有任务级尺子，不能只看 loss。评估过了才谈蒸馏剪枝等轻量化，否则在已经糊的模型上继续压。"
        return "量化改完必须对账：余弦、偏差、任务指标。尺子没过就动轻量化，等于在误差上叠误差；LLM 还要另加生成向指标。"
    if T("轻量化") or T("蒸馏") and T("剪枝", "协同"):
        return "比特砍完体积还不够，才蒸馏、剪枝并与量化协同。轻量化是换结构，不是再拧一次 scale；组合拳打完这章才收口。"
    if T("量化基本原理") or (T("数学公式") and T("量化")):
        return "前面量化章讲怎么做，这段把映射公式摊开。公式清了才谈 per-tensor/per-channel，否则粒度和校准都在瞎调参数。"
    if T("Per-tensor") or T("Per-channel") or T("量化粒度"):
        return "公式有了，粒度决定一套参数管多宽。粒度选完，校准集才知道要覆盖什么分布；粒度错了，后面校准方法再精也救不回来。"
    if T("校准集") or T("标定数据"):
        return "粒度定了，校准集必须代表线上分布。集子歪了，MinMax/KL 再精也定不出可用 scale，PTQ 流程会整段空转。"
    if T("校准方法") or T("MinMax") or T("KL 散度") or T("Percentile"):
        return "有了合格校准集，才选 MinMax、KL、百分位。方法定了，PTQ 才能按步复现；方法没选稳，完整流程只是把错误跑一遍。"
    if T("scale") and T("LSQ", "PACT", "学习"):
        return "QAT 里 scale 不再手估。学习式量化把尺子也训进去，激活长尾的难点才会暴露，下一步才轮到 SmoothQuant 挪难度。"
    if T("SmoothQuant") or T("激活量化"):
        return "scale 可学之后，激活长尾仍会打爆 INT8。SmoothQuant 把难度挪到权重，Weight-only/GPTQ 那条才接得上。"

    # ----- 模型转换 / ONNX / 引擎 / 编译 -----
    if T("模型转换") and not T("OMC"):
        return "部署主链路从交接面开始：训练框架出图，先转成引擎吃得下的中间格式。图对了才谈编译和 Runtime，转换失败不要先怪板上。"
    if T("推理引擎") and T("编译"):
        return "转换只交出图。引擎和编译决定融合、精度策略和能跑的 kernel。编出来才有运行时可调度，否则时延账无处落地。"
    if T("运行时") or T("调度"):
        return "引擎产物要有人加载、排队列、占核。调度不清，转换和编译再漂亮也交不出时延；主链路到这里才算闭环。"
    if T("ONNX") and T("StableHLO", "TOSA", "IR", "vs"):
        return "导出只是第一跳。ONNX、StableHLO、TOSA 各吃不同后端，选错中间格式，后面图匹配失败会整段返工。"
    if T("torch.export") or T("Dynamo") or T("FX"):
        return "编译器章从导出抓图开始。export/FX 图不对，后面换 IR、配 kernel 都是空的；图稳了才比较 ONNX 与各方言。"
    if T("图模式匹配") or T("典型 LLM 算子"):
        return "IR 选好仍会在 LLM 算子上匹配失败。先认哪些图模式吃不住，再谈自写 kernel，否则 NPU compiler 只能报一串不支持。"
    if T("Kernel 库") or T("各吃哪一段"):
        return "匹配失败才知道要补哪段 kernel。库是按图区间分工的，弄清各吃哪一段，端侧 NPU compiler 才有配置语言。"
    if T("NPU compiler") or T("compiler 共性"):
        return "kernel 分工清楚了，看各家 NPU 编译器的共性：切图、选核、回落 CPU。共性懂了，动态 shape 的折中才好谈。"
    if T("动态 shape") or T("seq_len"):
        return "NPU 编译常假设静态形状。动态 seq_len 要在 padding、分档、再编译之间折中；折中定了，融合白名单才不会把动态图融死。"
    if T("算子融合") or T("融合白名单"):
        if T("白名单"):
            return "动态形状有折中后，才规定能融与不该融。乱融会藏精度坑，该融不融又把碎算子留给 profiler；下一步用 dump 验证。"
        return "瓶颈若在碎算子，先融合少写回。融合完 KV 内存墙才会露出来；没定位就融，容易把精度和动态 shape 一起融坏。"
    if T("graph dump") or T("layerwise") or (T("调试") and T("dump")):
        return "融合和回落是否真按白名单发生，要靠 graph/layerwise dump 核对。编译器章收到这里：能看见图，才能排「能转不能跑」。"

    # ----- Prefill / Decode / TTFT / KV -----
    if T("性能分析") or T("定位瓶颈"):
        return "量化过线才谈快。先 profiler 定位热点，再动融合或 KV，别一上来改 kernel；找错瓶颈，后面每一招都在空转。"
    if T("计算图优化"):
        return "瓶颈若在碎算子和小启动，先做图优化与融合。计算省下来之后，生成时长对话的 KV 内存墙才会变成下一道题。"
    if T("KV-Cache") or T("KV Cache") or T("KV缓存") or (T("KV") and T("动态内存", "显存计算", "原理")):
        if T("Paged") or T("Offload"):
            return "KV 原理和显存公式有了，才上分页、卸载、KV 量化。布局招用对了，Prefill/Decode 两个阶段才好分开治。"
        return "图优化省的是计算，长对话吃的是 KV。缓存账管住了再抠 DDR 带宽；KV 没算清，Token 速度优化只是加核空转。"
    if T("内存带宽") or T("DDR"):
        return "KV 布局再好也要过总线。带宽账清了，Decode 的 Token 速度才有优化空间，否则生成慢会被误判成算力不够。"
    if T("Token") and T("生成", "速度"):
        return "带宽和 KV 有数，才优化 Decode 吞吐。自回归一步一 token 仍慢，下一步才上投机采样，别把算法招提前用。"
    if T("投机采样") or T("Speculative"):
        return "自回归太慢才投机：用小模型猜、大模型验。改的是算法，Attention/GEMM kernel 是另一层；两招别搅成一锅。"
    if T("Attention") and T("GEMM", "内核"):
        return "算法招用尽，热点还在 Attention/GEMM，才下钻 kernel。这是性能章最后扳手，前面没定位就改核等于盲拧。"
    if T("prefill") or T("Prefill") or T("Decode") or T("decode"):
        if T("Profil"):
            return "端到端 TTFT/TPOT 有定义了，还要按 Prefill 与 Decode 分层 profiler。两阶段治法不同，混着看会把首字慢和跟手慢治反。"
        return "KV 布局之后要把生成拆成 Prefill 与 Decode。首字慢和跟手慢不是同一笔账；阶段认清，TTFT 指标才有意义。"
    if T("TTFT") or T("TPOT") or T("性能指标"):
        return "算子级认知之后，把体感收成 TTFT/TPOT/吞吐。指标权衡清楚，调参才有基线；没定义就改引擎，绿数字对不上产品。"
    if T("FlashAttention"):
        return "投机采样改算法，FlashAttention 改的是 Attention 实现。算子级认知立住，才谈 TTFT 指标和后面的引擎开关。"
    if T("调优实验") or T("profiler"):
        return "指标定义清楚，才按基线→profiler→逐项改参跑。实验框架有了，TensorRT-LLM 量化选型才不是碰运气。"

    # ----- QNN / TensorRT / 平台 -----
    if T("QNN") or T("高通"):
        if T("经验迁移"):
            return "KV 与 Prefill 方法论有了，把昇腾上的转换-量化-板上验收迁到 QNN。厂商换了，链路角色不能丢，下一步才是 TRT 桌面与车端差异。"
        return "编译器共性讲完，落到高通：图要进 Hexagon/NPU。QNN 跑通，才对比英伟达 TensorRT，两条实链不要混着配。"
    if T("TensorRT") or T("英伟达") or T("Jetson") or T("Orin"):
        if T("Edge-LLM") or T("桌面"):
            return "QNN 迁完，看 TensorRT 在端侧 LLM 上和桌面版差在哪。机制对齐了，才谈车规 OTA 与批次一致性，别拿桌面 demo 当量产。"
        if T("TRT-LLM") or T("TensorRT-LLM") or T("量化选型"):
            return "调参框架有了，才在 TensorRT-LLM 里选量化档和命令流。选型落地后，用精度-资源矩阵收口，再决定要不要转 GGUF。"
        if T("工程深挖") or T("交付纪律"):
            return "高通验收矩阵讲过，这段把 Jetson/TRT 的交付纪律钉死。厂商纪律齐了，昇腾双轨才好对照，避免各说各的绿。"
        return "高通链看过，英伟达走 TensorRT 图优化与引擎构建。版本和芯片对上，插件和精度才有意义；两家工具不要交叉套命令。"
    if T("麒麟") or T("HiAI"):
        return "昇腾盒子跑通，再看麒麟座舱板的 HiAI/.omc 边界。板型能力认清，MindSpore Lite 改造才知道能改到哪一层。"

    # ----- 门禁 / OTA / 工程化 -----
    if T("门禁") or T("OTA") or T("车规") or T("Checklist") or T("SOP"):
        if T("量产门禁") or T("运行纪律"):
            return "流水线能重复，才设「不过就不许上车」的门禁。纪律立了，车规与 OTA 才有挂载点；演示绿不等于放行绿。"
        if T("车规") or T("OTA") or T("合规"):
            return "门禁矩阵有了，才叠加车规、OTA 整包与合规。发布总清单是把这些检查收成一张表，值班 SOP 再裁成能执行的最短路径。"
        if T("Checklist") or T("发布"):
            return "车规与 OTA 条款要对进发布清单。清单过了，才允许裁成值班 SOP；没有总表就写速查，现场一定会漏项。"
        if T("SOP"):
            return "总清单太长不能值班。SOP 只保留可执行最短路径；门禁、OTA、安全的条款已经在前面立过，这里不重新讲道理。"
        return "流水线能重复，才上门禁、车规、OTA 与验签。演示绿不等于放行绿；少一项都会在回滚里爆，这是交付收口。"
    if T("工程化") and T("量产") and not T("门禁"):
        if T("自动化") or T("流水线"):
            return "量产路径走过，收成可重复流水线。流水线稳了才谈回归验证；手点绿不能当交付，后面资源评估才有输入。"
        if T("回归"):
            return "流水线能复现，回归才有意义：精度、性能、指纹一起看。回归绿了，资源评估才不是拍脑袋，文档才能当交接。"
        if T("资源评估"):
            return "回归证明还能再跑，才评估内存、算力、带宽够不够。资源账清了，落地文档才写得住，门禁章才能设硬阈值。"
        if T("文档") or T("沉淀"):
            return "资源账和回归结果要沉成文档才能交接。沉淀完，下一章才用门禁把「不许上车」写死，否则纪律没有附件。"
        return "板子会跑了，把训练到车机、工具链迁移、车规约束串成量产路径。路径有了，再收成流水线、回归和门禁，别停在单机 demo。"
    if T("自动化流水线"):
        return "量产路径走过，收成可重复流水线。流水线稳了才谈回归；手点绿不能当交付，后面资源评估才有输入。"
    if T("回归验证"):
        return "流水线能复现，回归才有意义：精度、性能、指纹一起看。回归绿了，资源评估才不是拍脑袋。"
    if T("资源评估"):
        return "回归证明还能再跑，才评估内存、算力、带宽。资源账清了，文档才能当交接，门禁才能设硬阈值。"
    if T("落地沉淀"):
        return "资源账和回归结果要沉成文档才能交接。沉淀完，下一章才用门禁把「不许上车」写死，否则纪律没有附件可挂。"

    # ----- 入门全栈其余主题 -----
    if T("机器学习") or T("深度学习基础"):
        return "进部署前先把训练/推理、过拟合这些词对齐。概念齐了才谈转换、量化、算子；词没齐，30 天路线只是清单。"
    if T("核心概念") and T("转换", "量化", "算子"):
        return "深度学习词齐了，这段把转换、量化、算子、异构硬件钉成一张图。图立住，后面学习路线才不是周历表。"
    if T("学习路线") or T("30天") or T("五阶段"):
        return "核心概念有了，再排五阶段路径，避免上来就抠平台命令。路线清楚才配三平台环境，CV 全链路才有周次可挂。"
    if T("三平台") or (T("SSH") and T("Conda")):
        return "路线图画完才装 SSH/ADB/Conda。环境通了，CV 那条 PT→ONNX 才有板子可跑；环境是主链路的手，不是目录装饰。"
    if T("AI编译器") and T("核心算子", "LLM优化"):
        return "引擎全景只告诉你有哪些栈。这段讲编译器和算子怎么把图画成能跑的核；排错章要靠这层语言，不能只记报错原文。"
    if T("常见问题") or T("排错") or T("调试知识库"):
        return "前面链路都走过，这段按全链路收口排错。先定位卡在转换、量化还是板上，再回头翻对应主题，别从日志第一行猜。"

    # ----- 前置底座 -----
    if T("大模型核心原理"):
        return "量化、编译默认假设你懂 Transformer。这段把主干原理立住，编程和硬件才接得上，否则后面全是名词。"
    if T("编程与编译基础"):
        return "原理懂了还要会读写图、编译产物。编译基础齐了，硬件体系才不是缓存和位宽的名词表。"
    if T("硬件体系"):
        return "软件栈要落到核、缓存、带宽上。硬件账清楚，后面量化位宽和 KV 才有物理上限，主链路的时延才解释得通。"

    # ----- LLM/VLM 补全与工程深挖（按概念，不报标题） -----
    if T("勘误"):
        return "补全章先把原文过时处钉掉。勘误清了，2026 的小模型选型才不会沿用旧约束；先纠错，再谈新格式。"
    if T("SLM") or T("小 VLM") or (T("选型") and T("2026", "端侧 SLM", "趋势对照")):
        if T("2026") or T("趋势"):
            return "任务级量化和门禁有了，才对照 2026 选型。趋势要能反推前面的内存、KV、精度约束，否则又是一张宣传表。"
        if T("Roofline") or T("预筛"):
            return "车规约束认清，用内存/带宽 Roofline 预筛模型。筛过了才上 VLM 多模态策略，避免先下载再发现塞不下。"
        return "勘误之后再选端侧 SLM/小 VLM。模型体积和上下文对得上板子，新量化格式才有真实约束可谈。"
    if T("量化新格式") or T("真实约束"):
        return "小模型选型有了，看新量化格式在端上真能跑哪些档。约束清楚，推理算法补全才不会按云端假设写。"
    if T("推理算法补全"):
        return "格式约束认清，才补端侧视角的推理算法。算法补完，Tokenizer 与模板必须对齐，否则采样再巧也接不上词表。"
    if T("Tokenizer") or T("Chat Template"):
        return "算法补全要落在词表和对话模板上。模板不对，RAG 和工具调用会整段错位；先对齐再接检索。"
    if T("端侧 RAG") or (T("RAG") and T("切块", "检索")):
        if T("切块") or T("混合检索"):
            return "工具调用链通了，RAG 才谈切块、混合检索和端上评测。检索质量没有端侧尺子，VLM 时序再接也是带错上下文。"
        return "模板对齐后才能在端上做 RAG。检索占内存和时延，要单独入账；LoRA/前缀共享是另一条省参路径，别和检索混谈。"
    if T("LoRA") or T("Adapter") or T("前缀共享"):
        return "端上改任务不一定重训。LoRA/Adapter 与前缀共享管的是参数增量；增量稳住，VLM 部署才不会把视觉塔一起微调翻车。"
    if T("VLM") and T("部署进阶", "进阶", "时序", "异构流水", "多模态", "差异化精度"):
        if T("时序") or T("异构流水线"):
            return "RAG 评测有了，VLM 还要把视觉编码和语言 Decode 串成异构流水。时序清了，KV 量化与前缀缓存才知道该切哪一段。"
        if T("多模态") or T("差异化精度"):
            return "模型预筛过了，VLM 要对视觉塔和语言塔用不同精度。策略定了，语音等其它模态才能复用同一套端侧纪律。"
        return "参数增量会了，VLM 还要处理视觉编码和交叉注意力。多模态链路立住，采样与安全兜底才有输入可守。"
    if T("采样与安全") or T("安全兜底"):
        return "VLM 能出字了，采样和安全兜底要一起设。兜不住就不要接内存公式去堆上下文，先保证乱说话能被拦住。"
    if T("内存公式") or T("预算表"):
        return "安全边界有了，才把权重、KV、激活写成完整内存公式。预算表是后面路径对比的尺子，没有公式选 ExecuTorch 或 QNN 都是猜。"
    if T("ExecuTorch") or T("路径对比"):
        return "内存预算有了，才对比 ExecuTorch、QNN HTP 等落点。路径选定，工程检查清单才能勾，否则清单只是厂商功能表。"
    if T("检查清单") or T("并入检查"):
        return "路径对比有结论，才收成工程检查清单。清单后面才定义 TTFT/TPOT；没有检查项，指标再完整也挂不进门禁。"
    if T("Serving") or T("共板资源"):
        return "精度三站过了，看端侧 Serving 边界和共板抢资源。资源账清了，才谈端云切分、OTA 整包和温区对 Decode 的影响。"
    if T("端云切分") or (T("OTA") and T("温区", "整包")):
        return "共板资源有数，才决定端云切分和 OTA 整包怎么发。温区会拖 Decode，长上下文策略必须按车上约束收，不能按云端窗口抄。"
    if T("长上下文") or T("RoPE") or T("滑动窗口"):
        if T("归一化") or T("RMSNorm"):
            return "注意力变体决定 KV 形状，RoPE/RMSNorm 决定位置和数值稳不稳。这两处钉住，FFN 门控变体才好对算子。"
        return "OTA 与温区约束之后，长上下文不能无限堆 KV。RoPE 外推和滑动窗口是省缓存的算法，工具调用要在窗口内仍找得到参数。"
    if T("工具调用") or T("Function Calling"):
        return "上下文策略定了，工具调用要把参数从生成里稳稳拆出。调用链通了，RAG 切块才有工具结果可拼，否则检索和函数各说各话。"
    if T("KV 量化") or T("Prefix"):
        return "VLM 时序清了，KV 才能量化、分页、做前缀复用。缓存组合选定，任务级量化验收和 CI 四站门禁才有内存基线。"
    if T("任务级量化") or T("CI 四站") or T("四站门禁"):
        return "KV 组合有基线，量化验收要按任务和 CI 四站过，不按单条 loss。门禁绿了，才配 2026 选型对照，否则趋势表没有门槛。"
    if T("精度对齐") or T("三站"):
        return "Prefill/Decode 分层看过，精度还要对齐三站并钉死 chat template。模板漂了，Serving 和门禁都会把「能跑」当成「能交」。"

    # ----- Transformer / 编译器栈 -----
    if T("编码器") or T("整体架构"):
        return "平台对照之前，先把 Transformer 编码器-解码器和核心算子立住。主干不清，Decoder-only 和 KV 变体都像名词卡片。"
    if T("Decoder-only") or T("因果注意力") or T("Causal"):
        return "整体架构有了，生成模型走因果注意力。掩码懂了，MHA/GQA/MQA 和 KV 形状才解释得通，否则缓存优化没有图。"
    if T("MHA") or T("GQA") or T("MQA"):
        return "因果注意力之上才选多头变体。GQA/MQA 直接改 KV 体积，后面 RoPE 和 RMSNorm 是位置与数值稳定，别和头数搅在一起。"
    if T("FFN") or T("SwiGLU"):
        return "位置编码稳定后，看 FFN/SwiGLU 吃掉的那截算力。前馈变体认清，VLM 视觉塔和交叉注意力才好接到同一套算子账。"
    if T("Swin") or T("Patch") or T("频谱"):
        return "VLM 视觉塔之外，窗口注意力和 Patch/频谱前处理是另一路图。图类认清，编译器前端 IR 才知道要降低什么算子。"
    if T("编译器栈") or T("前端 IR") or T("Codegen"):
        return "模型算子齐了，才拆编译器前端 IR、中端优化、后端生成。栈分层清楚，LLVM/MLIR/TVM 才不是三个并列名词。"
    if T("LLVM"):
        return "编译器栈分层后，LLVM 管指令选择和寄存器。Pass 懂了，MLIR 方言降低才有落点，不会把图优化和指令选择混谈。"
    if T("MLIR") or T("Dialect") or T("Lowering"):
        return "LLVM 之上用 MLIR 多层方言降低。降低路径清了，TVM 的 TE/Schedule 才是「怎么切循环」，不是又一种 IR 口号。"
    if T("TVM") or T("Schedule") or T("TE/TIR"):
        return "方言能降低，TVM 才谈计算表达和 tiling。调度空间懂了，GPU Warp/共享内存和端侧 OMG/IREE 才能对上硬件。"
    if T("CUDA") or T("Warp") or T("异构计算"):
        return "调度要落到 GPU 并行模型。Warp 和共享内存清楚，端侧图编译（XLA/昇腾 CANN/OMG、IREE）才知道能映射到什么核。"
    if T("图编译") or T("算子编译") or T("CANN") or T("IREE") or T("XLA"):
        return "GPU 并行有概念了，才看端侧图编译和算子编译入口。各家 lowering 不同，平台工具链扩展章才能按厂商对照，而不是抄同一条命令。"

    # ----- 平台扩展 / 昇腾实战 -----
    if T("跨平台运行时") or T("EP 落点"):
        return "各家工具链看过，对照运行时到底落到哪颗核。落点审计清楚，选型决策树才有输入，版本钉死才钉得住。"
    if T("选型决策") or T("反例"):
        if T("反例"):
            return "成熟度四级讲过，用反例打空话：芯片×模型×约束对不上的那些「都能跑」。反例集之后，版本钉死才知道要锁哪几个号。"
        return "运行时落点清楚，才做芯片×模型×约束的决策树。树画完，版本钉死清单才有对象，否则锁版本只是锁口号。"
    if T("版本钉死") or T("仓库布局"):
        if T("仓库"):
            return "空话反例见过，版本要落到仓库布局：驱动、编译器、Runtime、指纹各放哪。布局清了，两周节奏示例才抄得动。"
        return "选型有结论，把驱动、编译器、Runtime、模型指纹钉死。钉不住，附录产物名和评审提问都会变成各说各话。"
    if T("并入与维护"):
        return "版本清单要有人维护。约定写清谁改、何时作废，附录速查才不会和正文打架；维护约定是工具链章的胶水。"
    if T("产物名") or T("真伪校验") or T("名词别名"):
        if T("别名"):
            return "命令真伪能校验之后，把各厂商名词别名对齐。会上不混称，值班 SOP 和门禁表才能共用一套词。"
        if T("真伪"):
            return "两周节奏示例里的命令，要用真伪清单核对产物。假绿挡在仓库外，名词别名表才有资格统一会议语言。"
        return "版本钉死后，产物名要能对上日志。速查表是为了评审能问到文件而不是形容词；提问清单紧跟其后。"
    if T("评审提问"):
        return "产物名能对上，评审才问得出「文件在哪、指纹是谁」。防止空话过关之后，工程深挖才按厂商把排错矩阵铺开。"
    if T("能力成熟度"):
        return "昇腾双轨讲完，用跨厂商成熟度四级收口。级别认清，反例集才打得到空话，选型不会永远停在「都能试」。"
    if T("双轨") or (T("昇腾") and T(".om")):
        return "Jetson 纪律之后看昇腾云边 .om 与座舱 .omc 双轨。轨选错，后面跨厂商成熟度对比会把两套产物当成一个。"
    if T("两周节奏") or T("立项") or T("首包"):
        return "仓库布局能锁版本，才用两周节奏把立项到首包走一遍。示例不是作文，要用命令真伪清单核对每一步产物。"
    if T("达芬奇") or T("310B") or (T("昇腾NPU硬件") or T("硬件与达芬奇")):
        return "工具链对照完，实战先认达芬奇核和板型。硬件边界清了，CANN/DDK 的 FE/GE/TBE 才不是缩写表。"
    if T("DDK") or T("TBE") and T("CANN", "工具链"):
        return "板型认清，才拆 CANN 与 DDK：前端、图引擎、TBE、Runtime。工具链角色齐了，OMG 转 OMC 才知道每一跳谁负责。"
    if T("OMG") or T("omg") or T("离线模型"):
        return "DDK 角色齐了，用 OMG 把 ONNX 转成板上 OMC，量化配置一并编进去。转成功，TBE 算子搜索才有图可调。"
    if T("算子搜索") or T("tune_dump"):
        return "OMC 转出来，TBE 搜索才补缺核。搜索结果要进知识库，否则每次上板重新搜；命中机制是下一截。"
    if T("知识库") or T("hit_bank"):
        return "搜索结果要能命中知识库，调优才可复现。库稳了，才用 ADB 部署、看 model.csv 排错，别把偶然搜到当交付。"
    if T("ADB 部署") or T("测速") or T("model.csv"):
        return "知识库能命中，才上盒子测速和读结果表。板上数字对上了，再看麒麟座舱边界，两块板不要共用同一套预期。"
    if T("MindSpore"):
        return "麒麟能力边界认清，MindSpore Lite 改造才知道 NPU 能吃哪些 Transformer。改造范围清楚，量产全流程才接得上。"

    # ----- 量产 LLM 流程其余 -----
    if T("从云端训练到车机") or (T("全流程") and T("量产", "车机")):
        return "板端改造会了，把 LLM/VLM 从云端训练接到车机量产。全流程立住，Tokenizer 到采样的推理链才有位置挂，不会停在训练脚本。"
    if T("Tokenizer到采样") or T("推理全链路基础"):
        return "量产全流程有了，把推理从分词到采样串成可测链路。链路清了，INT4 混合精度才知道精度要钉在哪一站。"
    if T("混合精度") or T("W4A8"):
        return "推理链路可测，才上 INT4/混合精度。档位选完，Prefill/Decode 与 Roofline 方法论才有模型可套，否则优化没有对象。"
    if T("Roofline") and T("Prefill", "Decode", "方法论"):
        return "低比特档位有了，用 Prefill/Decode 和 Roofline 找瓶颈。方法对了，KV 管理才知道是算力墙还是内存墙。"
    if T("语音") and T("降噪", "增强", "RNN", "流式"):
        if T("流式") or T("动态量化"):
            return "语音增强模型定了，再做流式和 INT8 动态量化。实时链路跑稳，算子级 profiling 才有音频路径可对，不跟 LLM 抢同一套指标。"
        return "VLM 精度策略之后，语音降噪是另一条端侧网。模型选对了，流式与动态量化才接得上，别把 LLM 的 KV 账抄过来。"
    if T("三层Profiling") or T("算子级性能"):
        return "语音和 LLM 路径都有了，用三层 profiling 把热点钉到算子。这一层是量产优化的收口，前面 Roofline 没有算子证据就还是估计。"

    # ----- fallback：用前后概念，不写目录标题 -----
    ip = idea_clip(prev) if prev else ""
    it = idea_clip(t) or "本段"
    inn = idea_clip(nxt) if nxt else ""
    if ip and inn:
        return f"先把{ip}的验收做实，这段把{it}补上；下一步才动{inn}那层，否则容易跳步。"
    if ip:
        return f"先把{ip}做实，这段把{it}补上并收口；缺了这层，后面会对不上。"
    if inn:
        return f"这段先把{it}立住，给后面的{inn}垫底座；概念没齐就往下会跳步。"
    return f"这段把{it}讲清楚：它在链路里单独承担一截，细节在子点里练，不靠目录顺序硬背。"


def enrich_l3(leaf: dict, l2_title: str, l1_title: str, siblings: list[str]) -> None:
    t = strip_num(leaf.get("t") or "")
    raw = unwrap_template(t, leaf.get("d") or "")
    hit = match_concept(t)

    # Long markdown prose wins — do not crush tutorial body into slogan templates
    if raw and len(raw) >= 100:
        leaf["d"] = clamp(raw, 80, 1200)
        if hit:
            leaf["w"] = clamp(hit[1], 24, 100)
        else:
            old_w = (leaf.get("w") or "").strip()
            if old_w and not old_w.startswith("支撑「") and "才有抓手" not in old_w:
                leaf["w"] = clamp(old_w, 24, 90)
            else:
                leaf["w"] = clamp(f"弄清「{t}」，排障和选型时才知道该动哪一环。", 24, 80)
        leaf["b"] = ""
        return

    if hit:
        d, w = hit
        if raw and len(raw) >= 20 and raw not in d:
            if any(ch.isdigit() for ch in raw) or any(x in raw for x in ("×", "=", "→", "INT", "FP", "KV")):
                d = clamp(d + "（补充：" + raw[:60].rstrip("。") + "。）", 60, 280)
        leaf["d"] = clamp(d, 60, 280)
        leaf["w"] = clamp(w, 24, 100)
    else:
        if raw and len(raw) >= 18:
            d = clamp(f"{t}：{raw}" if not raw.startswith(t) else raw, 50, 400)
        else:
            d = clamp(
                f"{t}：承接「{strip_num(l2_title)}」。看它解决什么问题、验收看什么信号。",
                50,
                160,
            )
        old_w = (leaf.get("w") or "").strip()
        if old_w and not old_w.startswith("支撑「") and "一锅粥" not in old_w and "才有抓手" not in old_w:
            w = clamp(old_w, 24, 90)
        else:
            w = clamp(f"弄清「{t}」，排障和选型时才知道该动哪一环。", 24, 80)
        leaf["d"] = d
        leaf["w"] = w

    leaf["b"] = ""


def enrich_l2(node: dict, l1_title: str, prev: str | None, nxt: str | None) -> None:
    t = strip_num(node.get("t") or "")
    themes = [strip_num(c.get("t") or "") for c in (node.get("kids") or [])]
    themes = [x for x in themes if x][:6]
    cover = "、".join(themes) if themes else "若干子点"
    raw = unwrap_template(t, node.get("d") or "")
    hit = match_concept(t)

    # Prefer thick markdown section body over short CONCEPTS blurbs
    if raw and len(raw) >= 80 and "管端侧链路里这一段" not in raw and "别把目录当正文" not in raw:
        node["d"] = clamp(raw, 80, 2400)
        node["w"] = clamp(
            (hit[1] if hit else f"把「{t}」落到可验收信号上，再下钻子点。"),
            30,
            100,
        )
    elif hit:
        node["d"] = clamp(hit[0], 60, 280)
        node["w"] = clamp(hit[1], 30, 100)
    else:
        node["d"] = clamp(
            f"主题「{t}」下含：{cover}。先看验收标准，再点开知识点。",
            60,
            180,
        )
        node["w"] = clamp(
            f"给「{strip_num(l1_title)}」一个可讲可练的切口，让下面的知识点有归属。",
            30,
            90,
        )
    node["b"] = clamp(
        conceptual_bridge(t, prev, nxt, strip_num(l1_title), themes),
        40,
        140,
    )


def enrich_l1_placeholder() -> None:
    """L1 enrichment is inlined in main()."""
    return


def inject(path: Path, payload: str) -> None:
    html = path.read_text(encoding="utf-8")
    # Prefer TREE_MAIN when dual-tab is present; keep TREE_JD intact
    marker = None
    for cand in ("const TREE_MAIN = ", "const TREE = ", "const TREE="):
        if cand in html:
            marker = cand
            break
    if marker is None:
        raise SystemExit("TREE not found")
    start = html.find(marker)
    eq = html.find("=", start)
    i = eq + 1
    while i < len(html) and html[i] in " \n\r\t":
        i += 1
    if html[i] != "{":
        raise SystemExit("expected {")
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
    decl = "const TREE_MAIN = " if "TREE_MAIN" in marker else "const TREE = "
    new_html = html[:start] + decl + payload + ";" + html[k:]
    # soft UI copy tweaks
    new_html = new_html.replace(
        "是什么 / 作用 / 承接",
        "是什么 / 作用（主题层另有承上启下）",
    )
    new_html = new_html.replace(
        "是什么 / 作用 / 承接",
        "是什么 / 作用",
    )
    path.write_text(new_html, encoding="utf-8")
    print("injected", path.name, path.stat().st_size)


def main() -> None:
    tree = json.loads(TREE_JSON.read_text(encoding="utf-8"))
    tree["d"] = (
        "讲课序号 1→N。点开看「是什么 / 作用」。"
        "主题层多一句：这段在链路里补哪一环。"
        "高亮：琥珀=重点，珊瑚=核心。"
    )

    chapters = tree.get("kids") or []
    for i, c1 in enumerate(chapters, 1):
        t = strip_num(c1.get("t") or "")
        raw = unwrap_template(t, c1.get("d") or "")
        if raw and len(raw) >= 40:
            c1["d"] = clamp(raw, 40, 400)
        else:
            c1["d"] = clamp(
                f"「{t}」这一章把端侧部署里一块完整问题讲清楚；先看本章目标，再进主题。",
                40,
                120,
            )
        c1["w"] = clamp("排障时先回到这一章的目标，再下钻主题与知识点。", 24, 80)
        prev_ch = strip_num(chapters[i - 2].get("t") or "") if i > 1 else None
        nxt_ch = strip_num(chapters[i].get("t") or "") if i < len(chapters) else None
        kids_th = [strip_num(x.get("t") or "") for x in (c1.get("kids") or [])]
        kids_th = [x for x in kids_th if x][:8]
        c1["b"] = clamp(conceptual_bridge(t, prev_ch, nxt_ch, "", kids_th), 40, 140)

        l2s = c1.get("kids") or []
        titles = [strip_num(x.get("t") or "") for x in l2s]
        for j, c2 in enumerate(l2s):
            prev = titles[j - 1] if j else None
            nxt = titles[j + 1] if j + 1 < len(titles) else None
            enrich_l2(c2, c1.get("t") or "", prev, nxt)
            sibs = [strip_num(x.get("t") or "") for x in (c2.get("kids") or [])]
            for leaf in c2.get("kids") or []:
                enrich_l3(leaf, c2.get("t") or "", c1.get("t") or "", sibs)

    payload = json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
    TREE_JSON.write_text(payload, encoding="utf-8")
    for html_path in HTMLS:
        if html_path.exists():
            inject(html_path, payload)

    # stats
    b_l3 = b_l2 = 0
    n_l3 = n_l2 = 0
    for c1 in chapters:
        for c2 in c1.get("kids") or []:
            n_l2 += 1
            if (c2.get("b") or "").strip():
                b_l2 += 1
            for leaf in c2.get("kids") or []:
                n_l3 += 1
                if (leaf.get("b") or "").strip():
                    b_l3 += 1
    print(f"L2 with b: {b_l2}/{n_l2}; L3 with b: {b_l3}/{n_l3}")
    print("--- sample L2 b ---")
    sample_keys = (
        ("昇腾", None),
        ("量化基础", None),
        ("模型转换", "部署主链路"),
    )
    shown = 0
    for key, chap in sample_keys:
        for c1 in chapters:
            if chap and chap not in (c1.get("t") or ""):
                continue
            for c2 in c1.get("kids") or []:
                if key in (c2.get("t") or ""):
                    print("SAMPLE L2", c2.get("t"))
                    print(" b", c2.get("b"))
                    shown += 1
                    break
            else:
                continue
            break
    if shown < 3:
        # extra fallback samples
        for c1 in chapters:
            for c2 in c1.get("kids") or []:
                if (c2.get("b") or "").strip() and shown < 3:
                    if any(k in (c2.get("t") or "") for k, _ in sample_keys):
                        continue
                    print("SAMPLE L2", c2.get("t"))
                    print(" b", c2.get("b"))
                    shown += 1


if __name__ == "__main__":
    main()
