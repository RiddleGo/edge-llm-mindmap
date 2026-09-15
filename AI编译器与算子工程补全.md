# 🧩 ⑯ AI编译器与算子工程补全

> 主副本：图如何被 **导出 → 合法化 → 匹配 → 分块 → 选核 → 校验**。  
> 模型语义见 ⑨；量化算法见 ③；性能意图见 ④；平台命令见 ⑤ / ⑧ / ⑩ / ⑭。

---

### 1. torch.export / FX / Dynamo 与 ExecuTorch lowering

#### 职责划分

| 层 | 组件 | 产出 | 端侧含义 |
|---|---|---|---|
| 追踪 | Dynamo | 字节码级 guard + FX GraphModule | 抓住「这次前向」的静态图；guard 失败则再编译或回退 eager |
| 图 IR | FX (`call_function` / `call_module` / `get_attr`) | 可改写的 Python 图 | 融合、常量折叠、dtype 改写发生在这里 |
| 合法化导出 | `torch.export` → ExportedProgram | 带 FakeTensor 形状、常量、state_dict 的稳定图 | 比 `jit.trace` 更严：动态控制流必须 `cond`/`map` 或被特化 |
| 量化/改写 | `torchao` / PT2E / QDQ 插入 | 带 quantize/dequantize 的 FX | 必须与运行时 kernel 的 scale 语义一致（见 ③） |
| 端侧 lowering | ExecuTorch | Edge dialect → ExecuTorch IR → 后端 delegate | XNNPACK / QNN / CoreML / Vulkan / CPU 各吃一部分图 |
| 遗留路径 | `torch.onnx.export`（现多走 dynamo=True） | ONNX GraphProto | 仍是 QNN/ORT/部分 NPU 的进料口，**不是** ExecuTorch 主路径 |

#### 推荐链路（LLM 端侧）

```
Eager 模型
  → Dynamo 捕获（SDPA/MoE/变长 mask 常打断图）
  → torch.export（固定 example_inputs + dynamic_shapes 声明）
  → 可选 PT2E QDQ
  → to_edge_transform_and_lower / to_backend
  → .pte + 权重 blob
```

对照：`PyTorch → ONNX → qnn-onnx-converter` 仍是高通主路径（见 ⑤⑭），与 ExecuTorch delegate 是 **两条出口**，不要画成一条。

#### 工程检查点
- `export` 失败：Python 数据依赖控制流、未注册 custom op、`data-dependent` shape（如 `nonzero`）。
- 成功但变慢：图被切成多段 GraphBreak，中间回 Python。
- ExecuTorch：看 `delegation` 表——未委托节点落到 portable CPU，decode 会被拖死。

---

### 2. ONNX vs StableHLO vs TOSA vs Relay

同一计算，四种「合同」；编译器只认合同，不认 PyTorch 模块名。

| IR | 抽象层级 | 形状/控制流 | 典型下游 | 端侧现实 |
|---|---|---|---|---|
| **ONNX** | 框架无关算子表（opset 版本化） | `dynamic_axes`；控制流靠 If/Loop | ORT、QNN、OMG、TRT（部分） | **交换格式之王**；RMSNorm/RoPE/SDPA 常缺或版本漂移 |
| **StableHLO** | 稳定的 HLO 子集 | 动态维、量化类型更一等公民 | XLA、OpenXLA | 云侧/XLA 强；端侧看厂商是否吃 HLO |
| **TOSA** | 张量算子、偏移动/MCU | 静态可证明、量化类型内建 | MLIR TOSA → 移动 NPU / Arm | 适合静态量化 CV；LLM 动态 seq 很痛 |
| **Relay**（TVM） | 函数式图 IR | 符号 shape、控制流更完整 | TVM → TE/TIR | 定制后端强；与 ⑩ TBE/hit_bank 同类「搜索+知识库」 |

#### 选型口诀
- 进 **厂商 SDK**：优先对方官方入口（ONNX 或 `torch.export`），不要为 IR 干净强转三跳。
- 自研 codegen：StableHLO 或 MLIR 比 ONNX 更适合做 pass。
- **TOSA**：静态 INT8 卷积网，而不是 GQA+RoPE 自回归。
- **转换损失发生在合同边界**：ONNX 把 SDPA 拆成 MatMul+Softmax 后，NPU 融合模式就匹配不上。

---

### 3. 图模式匹配失败的典型 LLM 算子

编译器「有 fused kernel」≠「你的图能连上」。失败几乎总是 **图形状与白皮书模板不一致**。

#### SDPA
- 手写 `matmul + /sqrt + mask + softmax + matmul` → 匹配不到 FMHA，多次 DRAM 往返。
- mask 加性 `-inf` vs bool vs sliding window，模板只认一种。
- causal 用 `triu` 现算 vs `is_causal` 属性 → 多一个 Compare+Where 打断融合。
- dropout 训练残留 → 推理模板直接拒。
- **处理**：导出前 `F.scaled_dot_product_attention(..., is_causal=True)`；推理去掉 dropout。

#### RMSNorm
- 手写 `pow2 → mean → add eps → rsqrt → mul γ`，`axes`/`keepdims`/`eps` 位置不同则失败。
- **修复**：换成后端登记的 `RMSNorm` custom op，或与官方 pattern 逐节点一致。

#### RoPE
- `cos/sin` 每次 `arange` 现算 → 动态 shape + trig，NPU 几乎不融。
- interleaved vs half-split 两种布局，模板只认一种；YaRN/NTK 额外 Mul 使 pattern 失效。
- **修复**：cos/sin cache 作常量或 lookup；RoPE 做成单 custom op。

#### SwiGLU
- `SiLU(xW_g)*(xW_u)` 中间夹 to(dtype)/contiguous/bias → 无法 `fused_w1w3`。
- **不该融**：gate/up 已是 INT4 分组量化且 group 轴与拼接轴冲突时，强融会 pack 错。

#### GQA 的 `repeat_kv`
- `repeat_interleave` / `expand+reshape` / `broadcast` 三种写法；很多 NPU 要 **不 repeat、在 attention kernel 内广播 K/V 头**。
- 图上真 `repeat` 成 MHA 体积，④ 的 KV 带宽优化被编译器做废。
- **修复**：保持 `[B, kv_heads, T, D]`，把 repeat 交给 SDPA；禁止 export 前展开。

**通用手法**：失败子图做 graph dump 对照官方 golden 图；差一个 `Squeeze` 就整簇 miss。

---

### 4. Kernel 库：各吃哪一段

| 库 | 硬件 | 擅长 | 端侧角色 |
|---|---|---|---|
| **cuBLAS** | NVIDIA GPU | 大 GEMM | decode 的 `m=1` GEMV 往往不是最优 |
| **CUTLASS** | NVIDIA GPU | 可组合 GEMM、量化 epilogue | 自研 plugin / 量化 GEMM |
| **oneDNN** | x86/部分 Arm | 卷积/GEMM/LN | PC/工控 CPU；不是车规 NPU 主路径 |
| **QNNPACK** | 移动 CPU（量化） | NHWC INT8 卷积 | 老移动路径；LLM decode 收益有限 |
| **XNNPACK** | Arm/x86 CPU | FP16/INT8、ExecuTorch 默认 CPU delegate | 端侧 CPU fallback 与小模型 |
| **KleidiAI** | Arm CPU | SME/SME2、INT4/INT8 GEMM | 新 Arm 上 INT4 LLM 的关键 |
| **CMSIS-NN** | Cortex-M | 极小 INT8 卷积/FC | MCU 语音/检测；塞不进 7B |

**优先级**：NPU 厂商库 > KleidiAI/XNNPACK > 手写 NEON > 通用 BLAS。

---

### 5. 端侧 NPU compiler 共性

1. **静态 shape 偏好**：SRAM/指令按 shape 特化。动态维 → 多份编译、慢速通用核、或拒。
2. **权重预排布**：pad、interleave、INT4 nibble pack；运行时只 DMA。改量化粒度往往要整网重编。
3. **SRAM tiling**：激活切进 on-chip；tile 失败 = 反复进出 DRAM。
4. **DMA 双缓冲**：计算当前 tile 时 DMA 下一块；与 ② 的 runtime 内存池必须对齐。
5. **封闭算子集**：无设备端动态分配；softmax/reduction 轴须静态；精度以定点管道为准。

---

### 6. 动态 shape / 动态 seq_len 的工程折中

| 策略 | 做法 | 代价 | 适用 |
|---|---|---|---|
| **Padding** | 编译 `max_seq`，短序列 pad | 按最坏情况吃 SRAM | 延迟 SLA 松、NPU 完全静态 |
| **Bucket** | 编译 128/512/1024/2048 等档 | 产物变多、冷启动涨 | 车机预载 3–4 档常见 |
| **拆图** | prefill 静态大图；decode `q_len=1` + `kv_len=bucket` | 两套融合/两套校准 | **端侧 LLM 默认架构** |
| Chunked prefill | 长 prompt 切块 | TTFT 变差换峰值内存 | 与 ④ chunked 同一思想 |

**禁止幻想**：封闭 NPU 上完全动态 `seq` 且不损吞吐。`torch.export` 的 `Dim("seq")` 能导出，不代表 NPU lowering 能吃。

---

### 7. 算子融合白名单：能融 vs 不该融

#### 能融
- 逐点：`Add+Mul+SiLU/GELU`、QDQ 与随后 GEMM 的 scale epilogue。
- 归一化+残差：`RMSNorm + residual add`。
- Attention 簇：QKVO + scale + mask + softmax（SDPA/FMHA）。
- SwiGLU 的 gate/up 同输入、同量化方案时的成对 GEMM。

#### 不该融
- 跨精度边界：INT4 GEMM 与必须 FP16 的 RMSNorm 强融。
- 跨动态/静态边界：RoPE 动态 `position_ids` 拉进静态 SDPA tile。
- `repeat_kv` 融进 Q 投影：GQA 胀成 MHA。
- 采样/KV append/tokenizer 不应进 NPU 图。
- 精度未过就开最高 fusion → layerwise dump 无法归因。
- 超大 fused kernel 超出 I-cache/SRAM → 应主动解融。

规则：**融的目标是减中间张量与 launch，不是把 Python 模块变成一个巨核。**

---

### 8. 调试：graph dump、layerwise dump、数值一致性、NaN

#### Graph dump（编译对不对）
导出后、lowering 后、后端分区后 **三份图**。查：SDPA 是否仍在、哪些 node fallback、QDQ 是否成对、`repeat_kv` 是否被展开。

#### Layerwise dump（数对不对）
固定同一 prompt、同一 weights、同一 dtype 参考（通常 FP16 CPU）。对齐点：embedding 出、每层 attn 出、MLP 出、lm_head logits。指标：余弦、max abs、top-k 一致率。必须记录：是否 fused、是否 INT8 softmax、KV 是否量化。

#### 数值一致性协议（一次只开一个开关）
1. FP16/BF16 未量化图 vs PyTorch  
2. 开融合后 vs 步骤 1  
3. 量化后 vs 步骤 2  
4. 真机 NPU vs 仿真  

#### NaN / Inf 高频源
| 源 | 机制 | 对策 |
|---|---|---|
| Softmax 上 `-inf` mask 在低精度下整行全 `-inf` | `exp` 全 0 | 保留至少一行有效；mask 用 dtype 最大负值 |
| RMSNorm `eps` 过小 + INT8 噪声 | rsqrt 爆炸 | 加大 eps；Norm 留 FP16 |
| RoPE 半精度 × 量化 Q | 溢出 | 位置编码 FP16、权重 INT4 |
| INT4 scale 未融对 | 错 scale → 巨大 logits | 核对 per-group 轴 |
| KV 量化饱和 | 新 token clip | 校准含长上下文 |
| 脏 SRAM / 错误内存复用 | overlapping liveness | 关内存复用对比 |

**定位顺序**：logits 是否 NaN → 从后往前第一层 NaN → 该层融合核还是分解核 → 关融合/升精度/查 mask。不要先重训。
