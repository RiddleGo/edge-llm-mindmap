# JD 能力缺口补全

> **定位**：与「端侧主线」**并列**的补全页，不是替代。主线仍走 `端侧模型部署.md`。  
> **为何单开**：对照推理/编译器岗 JD 审计后，指令流水、DSA/内存层次、DeepSeek MLA、框架源码向、TGI、Glow、RISC-V、集合通信、云 Serving 在主线里要么只点名、要么故意弱写（端侧 BS=1）。  
> **读法**：投递缺哪块补哪块；数字一律写条件，不当保证。端侧验收尺仍回主线 ⑬。  
> **和主线的边界**：本页负责「云侧/体系结构/源码地图」能说到哪一层；端侧门禁五表、QNN/Edge-LLM 操作、⑬ 验收——一律回主线，这里不重复教程。

---

## ① 体系结构补强 · 内存层次 · 并行度 · 指令流水

投递里写「熟悉 GPU/NPU 架构」却答不上「decode 卡在哪一层」，面试会立刻掉头问带宽。  
「算力够不够」之前，先问「搬不搬得动」。CPU / GPU / NPU / DSA 的存储层次与并行模型不同，却经常被一张「xx TOPS」糊弄过去。本节把四类器件对齐到同一套问题：近端存什么、远端存什么、LLM decode 卡在哪一层。

### CPU / GPU / NPU / DSA 内存层次

| 器件 | 近端（低延迟） | 中端 | 远端（大容量） | 端侧/推理常见瓶颈 |
|------|----------------|------|----------------|-------------------|
| CPU | 寄存器 → L1/L2/L3 | — | DRAM | 缓存命中、核间一致性；decode 逐步时 ILP 吃不满 |
| GPU | 寄存器 → Shared Memory（可与 L1 carveout） | L2 | HBM / GDDR | HBM 带宽、bank conflict；峰值 TC 兑不成 decode |
| NPU | on-chip SRAM / Scratchpad | 片上缓冲分区 | DRAM / LPDDR | 权重是否常驻、DMA 节奏、KV 是否打爆片外 |
| DSA | 专用缓冲（固定数据流拓扑） | 流水级缓冲 | 片外 DRAM | 格式转换、对齐、无法通用调度的边角算子 |

DSA（Domain-Specific Accelerator，领域专用加速器）：为某一应用域定制的硬件，靠专用运算、并行与存储层次换性能/能效（Dally et al., CACM 2020）。NPU 是 DSA 在神经网络上的常见形态；别把「有 NPU」自动等同「有通用 CPU 流水线」。

**Hopper H100（数量级例题，写清代际）**：寄存器文件很大；Shared Memory 最高约 **228 KB/SM**；约 **132 SM**、每 SM **4** 个第 4 代 Tensor Core；HBM3 带宽量级约 **~3 TB/s**（NVIDIA Hopper 架构公开材料）。**Ampere A100**：约 **108 SM**、Shared 最高约 **164 KB/SM**、HBM2 约 **~1.55 TB/s**。白皮书「×N 于上一代」是 peak 叙事，不等于端到端 decode 倍速。

**端侧 NPU**：片上 SRAM 吃激活 tile / 热数据；权重与长 KV 常落 LPDDR。主线〇的访存墙在这里落地——decode 每 token 扫权重，墙在搬。Orin / 手机级 SoC 再砍一档：片上 SRAM 更小、LPDDR 带宽更紧，任何「权重常驻」承诺都要拿 footprint 对表，而不是口头「NPU 加速了」。

**读表方法（面试可复述）**：

1. 先问：权重、激活、KV 各自落在哪一层？哪一层会打爆？  
2. 再问：DMA / HBM 通路的 sustained 带宽大概多少，不是 datasheet peak。  
3. 最后问：BS=1 decode 时算术强度大概几个 FLOPs/byte——多数时候会落到 Roofline 的 memory-bound 区。

拒收话术：「我们这颗 NPU 有 xx TOPS」却说不清片上 SRAM 容量、权重是否常驻、KV 是否每次都打片外。

- **四层对照** — CPU/GPU/NPU/DSA：近端快、远端大；瓶颈写在「哪一层打爆」
- **DSA≠通用CPU** — 领域专用；NPU 是其常见形态，勿套五级乱序叙事
- **H100/A100 数量级** — Shared/SM/HBM 写清代际；peak≠decode 倍速
- **端侧落点** — SRAM 吃热数据；权重与长 KV 常落 LPDDR；墙在搬
- **拒收 TOPS-only** — 无带宽/常驻/温区，数字进不了验收

### 并行度统一框架

不要把「并行」只理解成「多开几个线程」。三层分开问：

| 层级 | CPU | GPU | NPU（典型） |
|------|-----|-----|-------------|
| 指令级 | 超标量、SIMD（NEON/AVX） | Warp 内 SIMT（warp=32） | 向量槽 / 脉动阵列节拍 |
| 线程/核级 | 多核、SMT | Block / Grid、occupancy | MAC 阵列分区、多核 NPU |
| 数据级 | batch、seq | batch、seq、head | 端侧对话常 **BS=1** |

端侧 LLM 对话 **BS=1** 时，GPU 课上的 occupancy 故事经常失灵：算力单元等带宽。要问的是：有效带宽、权重是否常驻、KV 布局、温区能否 sustained——与主线〇/⑬ 同一把尺。

Prefill：长序列矩阵大，更可能靠近 compute-bound。Decode：逐步依赖上一步 token，算术强度常落到数 FLOPs/byte 量级，memory-bound（Roofline / FlashAttention 文中的 bound 定义可对读）。

**算术强度直觉（数量级，非保证）**：一次 decode step 对整模权重做近似「读一遍」量级的访存，算的是一层层 matmul 的少量 FLOPs。权重越大、带宽越窄，tok/s 上限越低。这就是为什么「量化档」在端侧常比「多几个 TOPS」更能改体验——量化先砍搬的量。

**和主线衔接**：〇 里「访存墙」不是口号；本节给墙的硬件坐标。⑬ 验收若只报峰值 tok/s、不报量化/常驻/温区，仍按主线拒收。

- **三层并行** — 指令级 / 线程核级 / 数据级；别混成「多开线程」
- **BS=1** — 端侧对话 occupancy 故事常失灵；问有效带宽与 KV 布局
- **Prefill vs Decode** — 前者偏 compute；后者常 memory-bound
- **算术强度** — FLOPs/byte；量化先砍搬的量，常比空加 TOPS 更改体验

### 指令流水（CPU 微架构）

经典五级直觉：**取指 → 译码 → 发射 → 执行 → 写回**。冒险三类：结构（争用同一部件）、数据（结果未就绪）、控制（分支未决）。超标量与乱序执行用 ILP 填气泡，缓存层次用命中率藏 DRAM 延迟。

和 LLM 的关系（教材类比，勿字面化成「五级导致 LLM 慢」）：

- Prefill 大矩阵：向量单元 / Tensor Core 有活干，更像「算力侧」。
- Decode 逐步：下一次计算依赖上一个 token，**指令级并行填不满**；真正的「冒险」常常是**带宽冒险**——权重与 KV 还在路上，执行单元空转。
- 所以：会背五级流水，却解释不了「NPU TOPS 很高、对话仍卡」，面试会挂在访存墙上。

**NPU 对照**：很多 NPU 是静态图 / 数据流调度，不是通用乱序 CPU。别把「五级流水」硬套到所有加速器；要问的是：图是否固定 shape、权重是否预排布、片上 SRAM 是否盖住热路径。

**面试最短答法**：

> Prefill 更像算力题；decode 更像搬数据题。五级流水解释 CPU 气泡；解释不了 NPU 上「TOPS 高仍慢」——那要看权重/KV 落在哪一层、DMA 是否跟得上。

- **五级直觉** — 取指→译码→发射→执行→写回；三类冒险填气泡
- **带宽冒险** — decode 逐步时墙常在搬，不在流水线级数
- **NPU 对照** — 静态图/数据流居多；勿硬套乱序 CPU
- **最短答法** — Prefill 算力题；decode 搬数据题；TOPS 高仍慢先查层次

---

## ② DeepSeek 主架构与 MLA

主线〇/⑬ 已覆盖 Qwen/Llama **端侧选型**。DeepSeek 主系（V2/V3）的差异在结构，尤其是 **MLA**；蒸馏小模型（如 R1-Distill-Qwen）≠ 讲得清主架构。简历写「熟悉 DeepSeek」却只能背参数量，会被追问：KV 怎么压、absorption 后 cache 里到底存什么。

### 从 MHA → GQA → MLA

| 机制 | KV 怎么存 | 生态与部署 |
|------|-----------|------------|
| MHA | 每层每 head 存 K、V | 标准、贵 |
| GQA/MQA | 多组 Q 共享更少 KV head | Llama/Qwen 常见；端侧友好 |
| MLA | K/V 压进低维 latent，推理主要缓存 latent（+解耦 RoPE 相关项） | DeepSeek-V2/V3；引擎要有对应实现 |

DeepSeek-V2 技术报告（**arXiv:2405.04434**）：MLA 用低秩联合压缩；相对其设定，每 token KV 元素量可落到约等于「很少 group 的 GQA」量级，同时报告质量可强于 MHA（消融结论，需同设定）。相对自家 67B 基线，文中给出 KV **约 ↓93.3%**、生成吞吐 **约 ×5.76** 等部署数字——**基线是 DeepSeek 67B + 其服务配置**，不是「对任意 GQA 模型的普适定律」。DeepSeek-V3（**arXiv:2412.19437**）沿用 MLA；absorption 后推理不必从 cache 重建完整 K/V。

**吸收（absorption）口头版**：训练/定义里有「先投影再算 attention」的路径；推理可把部分投影吸进权重，使运行时主要读写压缩后的 latent cache，而不是每步展开完整多头 K/V。细节以论文与目标引擎实现为准——面试能说到「cache 布局变了、引擎要认」，比背公式更有用。

**解耦 RoPE**：MLA 常把位置相关项与内容 latent 拆开处理。导出/实现时若把 RoPE 路径弄丢或错误折叠，会出现「能跑但位置乱、长 ctx 崩」类问题。验收要有固定长上下文用例，不只看短 prompt 通不通。

- **MHA→GQA→MLA** — KV 从每头全量 → 共享 KV head → 低维 latent
- **93.3% / ×5.76** — V2 相对自家 67B 的条件数字，勿当普适定律
- **absorption** — 推理可吸投影；cache 主存 latent 语义
- **解耦 RoPE** — 位置项与内容拆开；导出丢路径会「短通长崩」

### 算子与部署影响

面试官要听的是「引擎能不能吃」：

1. Attention 是否实现 MLA 的 cache 布局与 absorption。  
2. RoPE（解耦项）、RMSNorm、MoE 路由（若有）是否在目标 Runtime 有 kernel。  
3. 导出路径（ONNX/自有格式）是否保留 latent 语义，而不是被错误展开成稠密 MHA。

端侧若强行上 MLA 大模型：先查 QNN / Edge-LLM / TRT 路径有没有对应算子。没有就诚实退回 GQA 小模型或云侧——比硬导出后静默 CPU fallback 强。

**和 Distill 小模型划界**：

| 你说的「DeepSeek」 | 实际结构 | 端侧含义 |
|-------------------|----------|----------|
| DeepSeek-V2/V3 主系 | MLA（+ 可能 MoE） | 要 MLA/MoE 算子与引擎支持 |
| R1-Distill-Qwen 等 | 多半是 Qwen 系 GQA 骨架 | 走主线 Qwen/GQA 路径即可；别吹 MLA |

拒收：「端侧已上 DeepSeek」——模型其实是 Distill-Qwen，却对外讲 MLA 收益。

**最小自学路径**：读 V2 报告 MLA 节 → 对照某一开源引擎（如支持 MLA 的 vLLM/SGLang 版本说明）看 cache 配置项 → 自己用一句话解释「相对 GQA，省的是什么、引擎多实现了什么」。端侧是否上马，另开算子门清单。

- **算子三问** — Attention cache 布局、RoPE/RMSNorm/MoE 核、导出是否保留 latent
- **端侧门** — 无 MLA kernel → 退 GQA 小模型或上云；禁静默 CPU fallback
- **Distill ≠ 主系** — Distill-Qwen 走 GQA；勿对外吹 MLA 收益
- **GQA 默认** — 端侧友好路径；主线已多用

---

## ③ 推理框架源码向

主线有 llama.cpp 的 backend dispatch、TRT-LLM/QNN 的**用法与开关**。JD 要的是：你能否在源码里指出 **谁管 KV 块、谁做 scheduling**。本节给读码地图，不替代整仓精读。目标：被追问「PagedAttention 的 block 默认多大」时，能答到版本与文件，而不是「好像是分页」。

### vLLM：PagedAttention 与 BlockManager

PagedAttention 把 KV 切成固定 **block**（类似操作系统页），按需分配，减少「按最大长度预分配」的碎片。源码里 `CacheConfig` 常见默认 **`block_size = 16` tokens**（可用参数改；以你 checkout 的版本为准）。

**BlockManager / BlockSpaceManager** 干的事：

- 维护逻辑 block ↔ 物理 block 映射（block table）
- 管理 GPU（及可选 CPU）块池
- prefix caching 时的引用计数与回收
- 与 scheduler 协作：序列结束释放块，新请求获得块

**Continuous / iteration-level batching**：每个 forward **迭代**后，完成的序列可以退出、新请求可以进入，不必等静态整批跑完。这和端侧「单用户 BS=1、固定会话」不是同一套问题——主线强调勿把 vLLM 队列语义搬进车机，就是这个原因。

**读码入口建议（跟一条路径即可）**：

1. `config/cache.py`（或同级）看 `block_size` 默认。  
2. Block manager：分配 / 释放 / block table 更新。  
3. Scheduler 主循环：本 iter 选哪些序列进 batch、哪些结束退场。  
4. Attention kernel 侧：如何用 block table 做 gather（概念层即可）。

先跟一条「请求入队 → 分配 block → 跑一步 → 释放」的路径，再谈优化（prefix cache、chunked prefill 等）。版本漂移快，**以你本地 checkout 为准**，面试说「我看的是某某 commit / 某版文档」。

**常见坑**：

- 把 `block_size=16` 说成「业界标准不可改」——它是常见默认，可配。  
- 把 GPU 块池耗尽当成「模型 bug」——其实是并发 × 长度把 KV 池打满。  
- 端侧照搬 continuous batching 叙事——车机单会话不需要这套队列语义。

- **block_size=16** — `CacheConfig` 常见默认；以 checkout 版本为准，可改
- **BlockManager** — 逻辑页↔物理页、池化、引用计数、与 scheduler 协作
- **iteration-level batching** — 每步可进可出；≠ 端侧单会话 BS=1
- **读码四步** — cache 默认 → block 分配释放 → scheduler → attention gather 概念

### TensorRT-LLM：IFB 与 plugin（对照 Edge-LLM）

云侧 TRT-LLM 文档中的 **In-flight Batching (IFB)** ≈ continuous / iteration-level batching：context 与 generation 可交织；效率上常要求 packed、少 padding。Attention 路径可选多种实现（文档中的 FlashInfer / TrtllmAttention 等），面向 inflight + paged KV。

**和 Edge-LLM 的差异（必须会说）**：

| | TensorRT-LLM（云/桌面叙事） | TensorRT Edge-LLM |
|--|---------------------------|-------------------|
| 定位 | 数据中心/工作站高吞吐 | Jetson/DRIVE 等边缘 C++ 运行时 |
| 调度 | IFB / Python 生态重 | 边缘部署约束不同 |
| 版本列车 | 与桌面 CUDA/TRT 绑定 | 与 JetPack/DRIVE OS 绑定 |
| 数字 | 桌面表 | **不可直接搬到 Orin 当验收** |

主线 Orin 表用 Edge-LLM；面试时分开说，避免「我跑过 TRT-LLM」被追问 Edge 路径时露馅。plugin / custom op 在云侧叙事里常见；Edge 路径要看对应版本是否暴露同等能力——以官方 Edge-LLM 文档为准，勿从桌面 TRT-LLM 文档外推。

- **IFB** — 云侧 continuous / inflight batching；context 与 generation 可交织
- **Edge-LLM ≠ 桌面 TRT-LLM** — JetPack/DRIVE 列车；数字不可直搬 Orin 验收
- **产品隔离** — 简历分开写路径；追问 Edge 时勿拿桌面文档外推

### SGLang 与 ONNX Runtime

**SGLang（RadixAttention）**：请求结束后 KV **不丢弃**，按 token 序列进 **radix tree**，新请求做最长前缀匹配复用；配合 cache-aware 调度（NeurIPS 2024）。多轮、共享系统提示时摊 Prefill；无命中时开销目标是可忽略。实现上前缀匹配可按 page 对齐（常见与 16 token 边界同类思路）。

**何时赚、何时不赚**：系统提示长且稳定、多轮共享前缀 → 赚 Prefill。每次 prompt 几乎全新 → 命中率低，别指望 Radix 救场。面试能说出这个分界，比背论文标题强。

**ONNX Runtime**：端侧常卡在 **EP 覆盖**（QNN / CUDA / CPU），不是「模型文件不会写」。验收要会：指定 EP → 看节点落点 → 发现静默 CPU fallback → 拒收或改图。主线 AI 编译器补全已有 fallback 审计口径，这里强调：源码/日志里要能指出 fallback 发生在哪一层。

- **RadixAttention** — 结束后 KV 进 radix tree；最长前缀命中摊 Prefill
- **何时赚** — 长且稳的系统提示 / 多轮共享前缀；每次全新 prompt 则不赚
- **ORT EP 落点** — 指定 EP → 查节点 → 静默 CPU fallback 直接拒收

---

## ④ 开源 Serving 对照（含 TGI）

端侧主线默认不上 vLLM/TGI；JD 仍要你能对照——「为什么不上」也要说得出理由，而不是「没听过」。

| 框架 | 官方定位（压缩） | 相对端侧主线 | 面试最小能力 |
|------|------------------|--------------|--------------|
| vLLM | 高吞吐 LLM Serving；PagedAttention + continuous batching | 概念必懂；默认不上车机 | 说清 block、scheduler、与 BS=1 边界 |
| SGLang | 快速 serving + 程序式生成；RadixAttention | 云/边；端上少见 | 前缀缓存何时赚、何时无命中 |
| TGI | HF 生态 Serving 工具包（Rust/Python 等） | 云侧 | 与 vLLM 取舍；**维护状态** |
| llama.cpp | 本地推理 | **主线已写透** | 作对照锚点即可 |

### TGI 维护状态与选型更新

**TGI 关键状态（2025 官方口径）**：Hugging Face 文档标明 TGI 进入 **maintenance mode**，新部署更推荐 **vLLM 或 SGLang**。面试若只吹 TGI「生产首选」而不提维护状态，会被认为信息过时。历史能力（continuous batching、TP、流式、量化）仍可作架构对照，但选型结论要更新。

**怎么答「TGI vs vLLM」**：

- 存量系统、HF 生态习惯、已有流水线 → 可继续维护 TGI，但要承认维护模式。  
- 新开云侧 Serving → 优先看 vLLM / SGLang 当前文档与你方模型支持矩阵。  
- 端侧 → 三者默认都不上车机；端侧锚点仍是 llama.cpp / QNN / Edge-LLM（主线）。

- **TGI maintenance** — 2025 官方 CAUTION；新部署优先 vLLM/SGLang
- **存量 vs 新开** — 存量可维护；新开看支持矩阵；端侧默认不上三者
- **不上车机的理由** — 队列语义、依赖体积、版本列车与功耗/车规约束

### 最小云侧实验（补主线弱项）

固定模型与量化 → vLLM 或 SGLang 拉起 → 打一条流式请求 → 记录 TTFT、tok/s、GPU 型号、并发。再拿同系列更小模型在端侧（主线路径）报一组数。目的不是比谁快，而是练习「场景不同尺不同」。

**建议笔记字段（抄进个人仓库即可）**：

| 字段 | 例 |
|------|----|
| 模型 + revision | `…` @ commit/tag |
| 量化 | FP16 / AWQ / … |
| 框架 + 版本 | vLLM x.y / SGLang a.b |
| GPU | 型号 × 卡数；TP 度 |
| 并发 | 1 / N |
| TTFT P50/P95 | ms |
| decode tok/s | 条件写清 |
| 是否流式 | 是/否 |

拒收：只有 Grafana 截图，无上表条件；或把云侧 IFB 吞吐写进车机验收。

- **笔记七字段** — 模型revision、量化、框架版本、GPU、并发、TTFT、tok/s
- **对照目的** — 练「场景不同尺不同」；不是比谁快
- **llama.cpp 锚点** — 端侧细节回主线 ⑧

---

## ⑤ AI 编译器谱系补缺（Glow · 前端 · 与主线衔接）

主线 ⑨ 已有 MLIR Dialect/Lowering、TVM TE/TIR、XLA/StableHLO、LLVM IR/Pass/SSA。本页补 **Glow 定位** 与「前端」口头图，避免谱系只背三个缩写。JD 写「熟悉 AI 编译器」时，要能画一条链，并知道哪一代东西已经 archived。

### Glow 放哪

Glow（Graph-Lowering，arXiv:1805.00907）：Facebook/PyTorch 系早期面向加速器的 NN 编译器——高层图 → 强类型 IR → 降到线性代数原语 → 后端 codegen（含 LLVM）。谱系上它是「框架图与硬件之间的 lowering 层」的一代实现。

**现网**：`pytorch/glow` 于 **2025-07-01 archived（只读）**。新课默认栈应是 **MLIR 生态（Torch-MLIR → IREE/厂商方言）、TVM、OpenXLA、torch.compile 后端、厂商编译器（QNN/CANN/TRT）**。Glow 用于回答「历史谱系」，不作量产默认路径。

**面试怎么提 Glow**：一句话定位 + archived 时间点 + 「今天我会从 MLIR/IREE 或厂商栈讲起」。停留在 Glow 细节却不知 archived，减分。

- **Glow 定位** — 框架图→强类型 IR→线性代数原语→codegen（含 LLVM）
- **archived 2025-07-01** — 谱系教材；非新项目默认
- **今日默认栈** — MLIR/IREE、TVM、OpenXLA、torch.compile 后端、厂商编译器

### 编译器前端要能画清

对「模型编译」面试，口头一条链即可：

1. **导入**：PyTorch/ONNX/厂商图 →  
2. **前端**：解析/校验、类型与 shape、图合法化（不是大学编译原理全套词法作业，但要知道「进不了 IR 的锅在这」）→  
3. **中端 IR**：MLIR dialect / TIR / StableHLO… 做融合、布局、常量折叠 →  
4. **后端**：指令选择 / 调度 / 寄存器或 NPU SRAM 分配 / codegen  

主线里的 SSA、Pass、LLVM IR 挂在中后端；端侧量产还多一刀：**静态 shape、权重预排布、禁止静默 CPU fallback**（见编译器补全文档）。

**前端常见翻车**：动态 shape 混进宣称静态的部署图；自定义 op 在导入期被丢掉或降成低效实现；类型/布局与目标 EP 不一致却在中端才爆。排查顺序：先确认「进了哪张合法 IR」，再谈融合对不对。

**与主线 ⑨ 分工**：主线写 Dialect/Pass/SSA 与端侧门禁；本页补 Glow 落点与「前端职责」口述。两边都要能指到文档，不靠背缩写表。

- **四段链** — 导入 → 前端合法化 → 中端 IR → 后端 codegen
- **前端翻车** — 动态 shape、丢自定义 op、类型布局与 EP 不一致
- **端侧多一刀** — 静态 shape、权重预排布、禁静默 CPU fallback
- **排查序** — 先确认进了哪张合法 IR，再谈融合对不对

---

## ⑥ RISC-V NPU 算子与模型

主线对 IREE→RISCV 只点到名。JD 写「基于 RISC-V NPU 的高性能算子和模型」时，要能描述一条可验证路径，而不是复读「开源友好」。没有板上数字时，诚实讲成熟度与风险，比空吹「已支持 LLM」安全。

### 能说到哪一层（IREE 官方 + 社区进展）

1. **主机**：IREE compiler 交叉生成 target module。  
2. **runtime**：按 RISC-V 目标构建。  
3. **llvm-cpu 后端**：`riscv32` / `riscv64`；可加 RVV feature（如 `+v`、`+zvl…`）走向量路径。  
4. **优化层（2025 仍在合入）**：面向 GenAI 的 **mmt4d ukernel**、VLEN-aware tiling 等——相对纯 LLVM 自动向量化可改善 matmul，但**不是**「已与 CUDA 栈对等的生产 LLM serving」。

QEMU 可作初学跑通；真机还要 HAL/驱动、内存对齐、量化格式。没有板上数字时，面试诚实讲：工具链成熟度、算子覆盖、风险清单。

**口头能力边界（建议照抄进笔记再改成自己的话）**：

> 我能把 IREE 的 llvm-cpu 路径指到 riscv64 + RVV feature，能描述 ukernel/tiling 在优化层的位置；真机 LLM 吞吐要以板子与算子覆盖为准，我不会把 QEMU 跑通说成生产 Serving。

- **四层路径** — compiler 交叉 → runtime → llvm-cpu(+RVV) → ukernel/tiling
- **边界** — 改善 matmul ≠ 与 CUDA 生产 LLM serving 对等
- **口头边界** — QEMU 跑通≠真机吞吐；无板上数字就讲风险清单

### 算子 → HAL → 板上（最小练习设计）

| 步骤 | 做什么 | 验收 |
|------|--------|------|
| 1 | 选一个算子（GEMM 或 Attention 子核） | 数值对金标 |
| 2 | IREE/TVM/厂商 DSL 实现或声明 | 可重复编译 |
| 3 | HAL 对接 NPU/CPU 后端 | 落点可查，禁静默错误 |
| 4 | 单层或微小模型上板/模拟 | 带宽与时延数量级 |

拒收话术：「我们支持 RISC-V」却说不清 triple、RVV 是否启用、有没有 ukernel、有没有真机。

**风险清单（可写进评审）**：向量长度（VLEN）与 tiling 假设不一致；量化格式与 DMA 对齐；缺少 Attention 融合核导致退回标量；驱动/固件版本与编译器 target 漂移。每一条都比「生态开放」更像工程语言。

- **最小四步** — 金标 → 可重复编译 → HAL 落点可查 → 板上/模拟数量级
- **拒收空话** — 说不清 triple / RVV / ukernel / 真机
- **风险清单** — VLEN、对齐、算子覆盖、版本漂移

---

## ⑦ NPU Runtime 自研要点

主线教的是 **用** QNN / CANN / Genie。JD「NPU runtime 开发」要的是你能设计/维护运行时本身。按交付物拆四块。不会写 runtime 没关系——要先会用主线的验收模板卡别人的 runtime。

### 四模块

| 模块 | 解决什么 | 常见事故 |
|------|----------|----------|
| 内存池 | 权重区 / 激活区 / KV 区；对齐与碎片 | 长会话 OOM；碎片导致「短 ctx 才活」 |
| 任务调度 | 图执行序、异步队列、CPU 回调 | 队列堵死；回调重入 |
| 算子加载 | kernel 注册表、版本指纹、CPU fallback | 静默 fallback 当「已加速」 |
| 异构同步 | DMA 完成、双缓冲、超时与取消 | 读到半成品；取消后泄漏 |

**内存池展开**：权重区通常长生命周期；激活区按层/ tile 复用；KV 区随会话增长。三者混在一个裸 `malloc` 池里，长会话最容易碎到「短 ctx 才活」。对齐按 DMA / 厂商要求来，不是按 CPU cache line 想当然。

**调度展开**：静态图可预先拓扑排序；动态或带控制流的图要明确「谁在 CPU 上做决策」。回调里再投稿入队，是重入经典坑——要有明确的线程模型。

**算子加载展开**：注册表要带版本指纹（引擎 ABI + 核版本）。生产配置应能 **禁 fallback**：缺核就失败，而不是悄悄跑 CPU 还报「NPU 推理成功」。

**同步展开**：DMA 完成前读缓冲 = 半成品；取消路径要回收 in-flight buffer，否则泄漏成「跑一会必挂」。

- **内存池三区** — 权重 / 激活 / KV；混池易碎到「短 ctx 才活」
- **调度纪律** — 拓扑序、异步队列；回调内再投递是重入坑
- **禁静默 fallback** — 缺核应失败；生产可关 CPU 路径
- **DMA 同步** — 完成前禁读；取消必须回收 in-flight

### 验收口径（可写进门禁）

1. 同图同输入两次跑，数值在协议公差内（对齐主线 ⑬-14 思想）。  
2. fallback 必须可观测（日志/计数器）；生产配置可禁 fallback。  
3. OOM 返回明确错误码，而不是进程被杀无现场。  
4. 版本指纹：引擎 + 驱动 + 模型哈希进交付清单（对齐主线 ⑮）。

和主线关系：你会用 Genie 不等于你会写 runtime；但主线的「落点审计 / 指纹 / 长稳」是自研 runtime 的验收模板。

**面试最小故事**：挑一个事故（静默 fallback 或 KV 池碎片）→ 你怎么观测 → 门禁怎么改。比空讲「四模块」更像做过。

- **数值门** — 同图同输入两次跑，公差内（对齐主线 ⑬-14）
- **可观测 fallback** — 日志/计数器；生产可禁
- **OOM 错误码** — 禁进程被杀无现场
- **指纹交付** — 引擎+驱动+模型哈希（对齐主线 ⑮）

---

## ⑧ 集合通信与多卡多 die

端侧主线 BS=1、单 die 交付。云侧多卡是加分项：要求概念正确，能解释「为什么多卡不等于单用户更快」。把「8 卡聚合 tok/s」写进车机体验，是主线明确拒收的口径之一。

### 集合通信与 Tensor Parallel

Megatron 式 **Tensor Parallel（TP）**（arXiv:1909.08053）：层内矩阵切到多卡——列并行与行并行组合；前向在行并行输出处用 **AllReduce** 汇总分片结果；每个 transformer block 前向大约涉及 **两次** 这类同步（attention 侧 + MLP 侧，细节随实现变体）。训练/推理里这些集合通信在 GPU 上常走 **NCCL**（或 NVLS 优先、NCCL fallback）。

教学要点：TP 切开了单卡算力/显存，但 **decode 每步**仍可能频繁同步——互联带宽与延迟变成新墙。TP 度要落在 NVLink 域内；跨节点硬上 TP，延迟会打穿 decode。

常见原语：AllReduce、AllGather、ReduceScatter。训练更重度用；推理 TP/部分 EP（Expert Parallel）也会碰到。EP 路由与 all-to-all 是另一套故事——面试能区分 TP（层内切矩阵）与 EP（专家分卡）即可入门。

**NCCL 口头层**：集合通信库；具体走 NVLink 还是 PCIe，由拓扑与运行时选择决定。简历写「熟悉 NCCL」至少要能说出：集合原语名字、TP 为何对延迟敏感、跨节点 TP 的风险。

- **TP + AllReduce** — 层内切矩阵；block 前向约两次同步量级（随实现变）
- **decode 新墙** — 步步同步；TP 度宜落 NVLink 域；跨节点 TP 易打穿
- **原语** — AllReduce / AllGather / ReduceScatter；推理 TP/部分 EP 也会碰
- **EP vs TP** — 专家分卡 vs 层内切矩阵；别混

### Pipeline Parallel 与多 die

| 策略 | 切什么 | 通信特征 | 滥用时的坑 |
|------|--------|----------|------------|
| Tensor Parallel | 层内矩阵 | 每步较频繁 | 跨弱链路 TP，decode 被通信淹没 |
| Pipeline Parallel | 层间 | 气泡、microbatch | 气泡填不满；调度复杂 |
| 多 die / chiplet | 片上多计算簇 | 片上互联 vs 片外 | 只加速封装内、忽略最慢跨封装链路 |

**层次**：**UCIe** 等 ≈ 封装内 die-to-die；**NVLink/NVSwitch** ≈ 服务器内加速器互联；PCIe/CXL 偏通用 I/O。集合通信落在哪一层，决定扩展规模。大模型放不进单 die 时，权重/激活分片跨 chiplet 或跨 GPU；端到端受**最慢链路**限制。

端侧交付时本节的用途：听懂云侧数字从哪来，拒绝把「8 卡聚合 tok/s」写成单用户体验（与主线 Edge-LLM「BS=1」口径一致）。

**一句话拒收**：多卡数字可以上云侧报告；进端侧门禁必须换算成单会话、单 die、带温区的尺。

- **PP 气泡** — 层间切分；microbatch 填不满就亏
- **UCIe vs NVLink** — 封装内 die-to-die vs 服务器内加速器互联
- **最慢链路** — 跨 chiplet/跨 GPU 受最慢一跳限制
- **聚合≠单用户** — 8 卡 tok/s 不进车机体验验收

---

## ⑨ 三端部署对照（云 Serving 补强）

主线〇已钉端 / 近边 / 云定义与切分。主线弱在：**云侧一条可复现 Serving 实验**。本节补实验设计，不重复 QNN 教程。做完第四节的对照表，本节要求你真的跑通一次并留笔记。

### 三端各自交什么

| 层 | 主仓库路径 | 本页要求你能交的 |
|----|------------|------------------|
| 端侧 | QNN / Edge-LLM / llama.cpp / ExecuTorch | 主线已覆盖；本页不重复操作 |
| 近边 | MEC / 园区盒 | 切分表、超时上推、失败回落（见〇） |
| 云 | MindIE 点名 + 本页 Serving | vLLM 或 SGLang：**拉起 → 请求 → 指标** |

近边不是「第二台假端侧」：它吃的是超时上推、断网回落、隐私与带宽预算。切分表在主线〇；本页只要求你能解释「为什么这条请求不上云 / 不下端」。

- **端侧** — 主线路径已覆盖；本页不重复操作
- **近边** — 切分/超时上推/失败回落；不是假端侧
- **云** — vLLM 或 SGLang：拉起→请求→指标

### 云侧最小可复现（建议写进个人笔记）

1. 固定开源模型与量化档（写清 repo revision）。  
2. vLLM 或 SGLang 启动（写清版本、GPU 型号、TP 度若有）。  
3. 同一 prompt 集：记录 **TTFT P50/P95**、**decode tok/s**、并发数、是否流式。  
4. （可选）同系列更小模型走端侧主线路径，并列表对比——只对比「尺是否写清」，不对比「谁赢」。

拒收：只有 Grafana 截图，无模型/量化/版本/并发；或把云侧 IFB 吞吐写进车机验收。

- **四步实验** — 固定模型量化 → 启动写清版本/GPU/TP → 记 TTFT/tok/s/并发 → 可选端云对照
- **拒收截图** — 无条件字段的 Grafana 不算复现
- **口径隔离** — 云 IFB 吞吐不进车机门禁

### 和主线拒收尺的衔接

云侧同样忌「最高 tok/s」无条件。端侧五表（内存、TTFT、稳态、掉点、温控）在云侧变形为：显存峰值、TTFT、吞吐、正确性、限流与尾延迟。思想同构，场景不同。

**云侧五问（对照端侧五表）**：

| 端侧五表思想 | 云侧变形 |
|--------------|----------|
| 内存 | 显存峰值 / KV 池占用 |
| TTFT | TTFT P50/P95 |
| 稳态 tok/s | 给定并发下的 decode 吞吐 |
| 掉点 / 正确性 | 金标或协议公差 |
| 温控 / 长稳 | 限流、尾延迟、长时间跑是否漂移 |

状态更新：新云部署优先 vLLM/SGLang；TGI 维护模式见④。端侧数字与验收仍回主线 ⑬。

- **云侧五问** — 显存峰值、TTFT、吞吐、正确性、限流与尾延迟
- **思想同构** — 与端侧五表同一套「有条件的尺」
- **状态更新** — 新云优先 vLLM/SGLang；端侧验收回主线 ⑬

---

## 出处速查（本页）

| 主题 | 优先文献 |
|------|----------|
| Roofline / 访存墙 | Williams Roofline；主线〇 Cambricon-LLM |
| GPU 层次 | CUDA Hopper/Ada Tuning Guide；A100/H100 白皮书 |
| DSA | Dally et al., CACM 2020 |
| MLA | DeepSeek-V2 arXiv:2405.04434；V3 arXiv:2412.19437 |
| vLLM | 官方文档 + `CacheConfig` block_size |
| TRT-LLM / Edge-LLM | NVIDIA 官方 docs（分产品阅读） |
| SGLang | NeurIPS 2024 RadixAttention |
| TGI | HF 官方 docs（含 maintenance 说明） |
| Glow | arXiv:1805.00907；GitHub archived 2025-07-01 |
| IREE+RISC-V | iree.dev RISC-V / llvm-cpu 指南 |
| TP / NCCL | Megatron-LM arXiv:1909.08053 |

数字进简历或答辩材料时，以你自己的复现为准；上表只作认方位锚点。
