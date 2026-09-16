# JD 能力缺口补全

> **定位**：与「端侧主线」教材**并列**的补全页，不是替代。  
> **来源**：对照推理/编译器岗 JD 审计后的缺口（指令流水、DSA 内存层次、DeepSeek MLA、框架源码向、TGI、Glow、RISC-V NPU、集合通信、云 Serving）。  
> **读法**：主线仍走 `端侧模型部署.md`；投递/面试缺哪块，来本页补哪块。

## ① 体系结构补强 · 内存层次与并行度

CPU / GPU / NPU / DSA 的「能算多快」往往先被「搬得动吗」卡住。四类器件内存层次不同，并行度模型也不同。

### CPU/NPU/GPU/DSA 内存层次对照

| 器件 | 近端存储 | 远端存储 | 端侧常见瓶颈 |
|------|----------|----------|--------------|
| CPU | 寄存器 → L1/L2/L3 | DRAM | 核间一致性、缓存命中 |
| GPU | 寄存器 / Shared Memory | HBM / GDDR | HBM 带宽、bank conflict |
| NPU | on-chip SRAM / Scratchpad | DRAM / LPDDR | 权重常驻 vs DMA 搬运 |
| DSA | 专用缓冲（固定拓扑） | 片外 DRAM | 数据流对齐、格式转换 |

- **是什么** — 寄存器→缓存/SRAM→DRAM→Flash，延迟与带宽逐级变差
- **作用** — 解释为何 decode 吃带宽、为何 TOPS 兑不成 tok/s
- **拒收** — 只报峰值 TOPS、不报有效带宽与常驻体积

### 并行度统一框架

| 层级 | CPU | GPU | NPU |
|------|-----|-----|-----|
| 指令级 | 超标量 / SIMD | Warp SIMT | 向量 / 脉动阵列 |
| 线程/核 | 多核多线程 | Block / Grid | MAC 阵列分区 |
| 数据级 | batch / seq | batch / seq / head | batch 常=1（端侧） |

端侧 LLM 对话常 **BS=1**：GPU occupancy 叙事搬不过来；要问的是有效带宽与 KV 布局。

### 指令流水（CPU 微架构）

取指 → 译码 → 发射 → 执行 → 写回。冒险：结构、数据、控制（分支）。超标量与乱序提高吞吐，但 LLM decode 逐步依赖上一步 token，**指令级并行吃不满**，墙回到访存。

- **与 LLM 的关系** — Prefill 矩阵大，更吃算力与向量单元；Decode 逐步，更吃带宽
- **NPU 对照** — 许多 NPU 是数据流/静态图调度，不是通用 CPU 流水线；别把「五级流水」硬套到所有加速器

## ② DeepSeek 主架构与算子

端侧主线已有 Qwen/Llama 选型。DeepSeek 主系（V2/V3）的差异在 **MLA** 等结构，影响 KV 体积与算子实现，不能只看 Distill 端侧版。

### MLA 与 GQA 差异

- **GQA** — 多组 Q 共享较少 KV 头，瘦 KV，生态成熟（Llama/Qwen 常见）
- **MLA（Multi-head Latent Attention）** — 把 KV 压到低维潜空间再投影，进一步压 KV 带宽/显存；实现与导出路径更挑引擎

端侧若强行上 MLA 大模型：先查目标 Runtime 是否有对应 kernel；没有就退回 GQA 小模型或云侧。

### 算子与部署影响

- Attention / RoPE / RMSNorm / MoE 路由（若有）要分别看算子覆盖
- 蒸馏小模型（如 R1-Distill-Qwen）≠ 主架构等价；面试要分清「用过 Distill」和「讲得清 MLA」

## ③ 推理框架源码向

主线已有 llama.cpp dispatch、TRT-LLM/QNN **用法**。本页补 **scheduler / 内存池** 级认知，至少能读 vLLM 或 TRT-LLM 一条主路径。

### vLLM 要点（读源码地图）

- **PagedAttention / BlockManager** — KV 按 block 分页；block table 映射逻辑页→物理页
- **Continuous batching scheduler** — 请求动态进出 batch；与端侧 BS=1 场景不同
- **与端侧边界** — CUDA 依赖强；车机/手机勿默认搬队列语义

### TensorRT-LLM 要点

- 引擎构建期融合与 plugin（FMHA、attention plugin）
- runtime 侧 batch / KV cache 管理与 speculative 开关
- Edge-LLM / Orin 路径与桌面 TRT-LLM **版本列车不同**，数字不可直接搬

### SGLang / ORT

- **SGLang** — radix / prefix caching；多轮共享前缀时摊 Prefill
- **ONNX Runtime** — EP 选择、fallback 到 CPU 的审计；端侧常卡在 EP 覆盖而非「模型不会」

## ④ 开源 Serving 对照（含 TGI）

### 框架对照表

| 框架 | 定位 | 端侧主线态度 |
|------|------|--------------|
| vLLM | 云侧高吞吐 Serving | 概念要懂；默认不上车机 |
| SGLang | 前缀缓存 / 复杂程序式生成 | 云/边；端上少见 |
| TGI | HF 生态 Serving | 云侧；与 vLLM 对照部署 |
| llama.cpp | 本地/端侧友好 | **主线已覆盖** |

TGI：模型加载、连续批处理、与 HF 权重格式衔接；面试能说清与 vLLM 的取舍即可。

- **vLLM** — 云侧高吞吐；PagedAttention + continuous batching
- **SGLang** — prefix / radix caching；多轮摊 Prefill
- **TGI** — HF Serving；与 vLLM 对照部署与取舍
- **llama.cpp** — 端侧主线已覆盖；本页只作对照锚点

## ⑤ AI 编译器谱系补缺

主线已有 MLIR / TVM / XLA(StableHLO)。补 **Glow** 与「前端」边界。

### Glow

Facebook 早期 NN 编译器；教学上放在「图→IR→codegen」谱系里。端侧现网更常见 TVM/MLIR/厂商自研；Glow 多作谱系定位，不作默认量产路径。

### 编译器前端（要能口头画清）

源码/模型图 → 词法/语法（或导入器）→ AST/图 → 语义与类型 → 中端 IR（优化）→ 后端指令选择/调度/寄存器分配（或 NPU codegen）。

主线 ⑨ 的 LLVM IR / Pass / SSA 挂在这里：前端负责「进得了 IR」，中端改 IR，后端出机器码或 NPU 二进制。

## ⑥ RISC-V NPU 算子与模型

主线仅点到 IREE→RISCV。本页要求：能描述一条 **算子 → HAL → 板上** 路径。

### 路径草图

1. 选算子（如 GEMM / Attention 子核）
2. 在 IREE/TVM/厂商 DSL 中实现或声明
3. 经 HAL 对接 RISC-V NPU 驱动
4. 小模型（或单层）上板测带宽与正确性

没有板上数字时，面试只谈路径与风险：工具链成熟度、算子覆盖、量化格式。

## ⑦ NPU Runtime 自研要点

### 自研要交的模块

主线是 QNN/CANN/Genie **使用**。自研 runtime 要交的是：

| 模块 | 要解决的问题 |
|------|----------------|
| 内存池 | 权重区 / 激活区 / KV 区；碎片与对齐 |
| 任务调度 | 图执行序、异步队列、与 CPU 回调 |
| 算子加载 | kernel 注册、版本指纹、CPU fallback 审计 |
| 异构同步 | DMA 完成、双缓冲、超时与取消 |

验收：同图两次跑数值一致；fallback 可观测；OOM 有明确错误码。

- **内存池** — 权重/激活/KV 分区；碎片与对齐
- **任务调度** — 图序、异步队列、CPU 回调
- **算子加载** — 注册、指纹、fallback 可审计
- **异构同步** — DMA、双缓冲、超时取消

## ⑧ 集合通信与多卡多 die

端侧主线 BS=1；云侧多卡是 JD 加分项。只要求概念过关。

### 集合通信

- AllReduce / AllGather / ReduceScatter（训练更常见；推理 TP 也用）
- NCCL（NVIDIA）等库；带宽与拓扑（NVLink / PCIe）决定策略

### 推理并行

| 策略 | 切什么 | 通信特征 |
|------|--------|----------|
| Tensor Parallel | 层内矩阵 | 每步较频繁 |
| Pipeline Parallel | 层间 | 气泡与 microbatch |
| 多 die | 片上多计算簇 | 片上互联 vs 片外 |

端侧单 die 交付时，本节用于「知道云侧在干什么」，避免把多卡吞吐数字当成单用户体验。

## ⑨ 三端部署对照（云 Serving 补强）

### 端 / 近边 / 云路径

| 端 | 主路径（本仓库） | 本页补强 |
|----|------------------|----------|
| 端侧 | QNN / Edge-LLM / llama.cpp / ExecuTorch | — |
| 近边 | MEC / 园区盒 | 与端的切分表（〇） |
| 云 | MindIE / 概念点名 | vLLM / TGI 最小可复现：拉起 → 打一条请求 → 看吞吐与 TTFT |

云侧最小实验：固定模型与量化，报 TTFT 与 tok/s，注明 GPU 型号与并发；再对比端侧同模型小一号的数字——体会「场景不同尺不同」。

- **端侧路径** — 主线已覆盖；本页不重复
- **近边路径** — 切分表见〇；超时上推与回落
- **云 Serving 最小实验** — vLLM/TGI 拉起→请求→TTFT/tok/s（写清 GPU 与并发）
