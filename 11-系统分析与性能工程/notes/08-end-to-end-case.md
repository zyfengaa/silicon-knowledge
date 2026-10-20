# 08 — 训练系统的硬件预算推导：从 6N FLOPs 到显存与 MFU

## 为什么讲这个

前面的笔记分别讲了 Roofline、Amdahl/Gustafson、功耗与散热、异构系统，以及 CPU/GPU/TPU 的 profiling 工具。到了真实的大模型训练，工程师最先要回答的不是“某个 kernel 快不快”，而是一组更靠前的预算问题：给定模型规模、token 数、序列长度和精度，需要多少算力、多少显存、多大网络、多少电，最后要花多少钱？

本篇把这些问题串成一条可复算的硬件预算链。GPT-3 175B 和 Llama 3 70B 是两个锚点：前者说明 6N FLOPs 和 MFU 的历史口径，后者给出一个可以逐项代入的现代 worked example。并行策略、ZeRO 分片、All-Reduce 算法和 NCCL 调优不在本篇展开，文末给出边界与延伸阅读。

## 1. 算力预算：6N FLOPs 的推导

### 1.1 前向 2N，反向 4N

设模型参数量为 `N`，训练 token 数为 `D`。对一个参数矩阵 `W`（`N` 个元素）做一次前向矩阵乘，每个 token 需要 `N` 次乘加；按“一次乘加 = 2 FLOPs”的惯例，前向是 `2N` FLOPs/token。

反向要算两个梯度：对输入的梯度 `dX` 和对权重的梯度 `dW`。两者各需要一次与 `W` 同规模的矩阵乘，因此各 `2N` FLOPs/token，反向合计 `4N`。

```text
前向:    C_fwd = 2 · N · D
反向:    C_bwd = 4 · N · D
训练合计: C_train = 6 · N · D
```

这就是 **6N 规则**。它统计的是“参数矩阵乘”的模型 FLOPs，不含注意力分数、归一化、softmax、逐元素操作和通信。

### 1.2 6N 的适用边界

6N 很好用，但它有明确的适用条件。下面任何一条不成立，都要修正：

- **只统计参数矩阵乘**：embedding 查表、LayerNorm、softmax、残差相加、激活函数都不计入。对标准 Transformer，这些项通常占比不大，但不是零。
- **不含注意力的 `s²` 项**：注意力核心是 `QK^T` 和 `PV`，每个 token 的计算量随序列长度 `s` 增长。它与 6N 项的比值近似为：

```text
C_attn / C_6N ≈ (2/3) · L · s · h / N
```

  以 Llama 3 70B 为例（`L=80`、`h=8192`、`N=70e9`），`s=8K` 时约为 5%，`s=128K` 时约为 82%。**长上下文训练不能只用 6N 做预算。**
- **不含重计算**：全量 activation recomputation 会多跑一遍前向，硬件 FLOPs 变成 `8N`；选择性重计算介于 `6N` 和 `8N` 之间。
- **MoE 要分开算**：计算 FLOPs 用“每 token 激活的参数量”，显存账本用“总参数量”。用总参数量乘 6N 会把计算量高估数倍。
- **多 epoch 要乘轮数**：`D` 是实际参与训练的 token 次数；推理前向则是约 `2N` FLOPs/token，另加 KV cache 访存。

### 1.3 GPT-3 175B：理论下限与 21.3% 的口径

GPT-3 175B 使用 300B token 训练，按 6N 计算：

```text
C = 6 × 175e9 × 300e9 = 3.15e23 FLOPs
```

| 项目 | 数值 | 口径 |
|------|------|------|
| 参数量 `N` | 175B | 稠密模型 |
| 训练 token `D` | 300B | 预训练 token 总量 |
| 总模型 FLOPs | `3.15e23` | 6N，不含重计算和注意力额外项 |
| 训练硬件 | 约 10,000 张 V100 | Microsoft Azure，非 A100 |
| 单卡峰值 | 125 TFLOPS | FP16 Tensor Core，稠密 |
| 理论最短时间 | 约 70 h | `3.15e23 / (1e4 × 125e12)` |

```text
T_peak = 3.15e23 / (10,000 × 125e12)
       = 2.52e5 s
       ≈ 70 h

T_actual(21.3%) = 70 h / 0.213
                ≈ 329 h
                ≈ 13.7 d
```

**21.3% 的口径**：这是常见的工程反推值，不是 GPT-3 论文正式报告的 MFU。它的分子是 6N 模型 FLOPs（`3.15e23`），分母是 10,000 × V100 稠密 FP16 峰值（`1.25e18 FLOP/s`），并对应约 329 h（13.7 天）的墙钟时间假设。GPT-3 论文没有以 MFU 形式报告效率，也未给出可直接复算的完整墙钟时间和峰值口径，因此引用时应把“6N + V100 125 TFLOPS + 约 13.7 天”一起写出，不要把它和 PaLM 的 46.2% 当作同一实验口径直接横比。

## 2. 显存预算：模型状态、激活值与 KV cache

### 2.1 模型状态：12 / 16 / 8 B/参数

训练时的模型状态由权重、梯度、FP32 master 权重和 Adam 一阶/二阶动量组成。不同框架和论文采用不同口径，常见的是下面三种：

| 口径 | 权重 | 梯度 | FP32 master | Adam m | Adam v | 合计 | 70B 总量 | 175B 总量 |
|------|------|------|-------------|--------|--------|------|----------|-----------|
| 16 B/参数 | 2 | 2 | 4 | 4 | 4 | 16 | 1.12 TB | 2.8 TB |
| 12 B/参数 | 2 | 2 | — | 4 | 4 | 12 | 840 GB | 2.1 TB |
| 8 B/参数 | 2 | 2 | — | 2 | 2 | 8 | 560 GB | 1.4 TB |

三种口径的由来：**16 B/参数**是标准混合精度训练，BF16 权重和梯度，另存 FP32 master 权重，Adam 的 `m`、`v` 保持 FP32，Megatron、PyTorch AMP 等常见配置对应此口径；**12 B/参数**去掉 FP32 master 权重，权重和梯度 BF16，Adam 状态仍为 FP32，部分 ZeRO/DeepSpeed 配置用它做估算，省 4 B/参数但更新精度要单独评估；**8 B/参数**把权重、梯度、一阶/二阶动量全部用 BF16（或 8-bit optimizer），是“能不能放下”的乐观口径，不应默认当作生产训练的实际占用。另外还有 14 B/参数（权重 2 + FP32 master 4 + Adam 8，不含梯度），只适合“权重 + 优化器”的局部估算，不要和完整训练状态混用。

模型状态的总量与并行切分方式无关，但每卡占用取决于切分：

```text
M_state = N · b_state
M_state_per_gpu ≈ N · b_state / (TP · PP)      # DP 复制，不减小模型状态
```

这里 `TP`、`PP` 是张量并行和流水线并行度。若使用 ZeRO/FSDP 对优化器状态或参数做分片，分母会变化；这部分属于并行策略，见文末链接。**引用显存数字时，必须同时说明“B/参数口径”和“每卡切分方式”**，否则 70B 既可能被算成 1.12 TB，也可能被算成 560 GB。

### 2.2 激活值

激活值是前向过程中为反向保存的中间结果。它没有一条放之四海而皆准的公式，但可以用下面的量级模型做预算：

```text
A_total ≈ L · s · b_micro · h · c_act
A_per_gpu ≈ A_total / (TP · PP · CP)
```

其中 `L` 是层数，`s` 是序列长度，`b_micro` 是每张卡（每个 DP 副本）的 micro-batch，`h` 是隐藏维度，`c_act` 是每层、每 token、每隐藏维度的等效字节数：

- 不做重计算：`c_act ≈ 30–40 B`；
- 选择性或全量重计算：`c_act ≈ 10–20 B`。

这些系数是工程估算，实际值取决于注意力 kernel、sequence parallel、是否使用 FlashAttention 以及框架的 buffer 复用。若显式物化注意力分数，还要额外计算：

```text
A_scores ≈ L · b_micro · n_heads · s² · bytes
```

这一项随 `s²` 增长，是长上下文训练显存爆炸的主因之一；FlashAttention 通过分块避免把完整的 `s × s` 矩阵写回 HBM，改变的是显存和访存，不是数学结果。

### 2.3 KV cache

推理的显存账本与训练不同：不需要梯度、优化器状态和大部分激活值，但每个并发序列都要保存 KV cache。

```text
KV_per_token = 2 · L · n_kv_heads · d_head · bytes_per_elem
```

因子 2 对应 K 和 V。使用 GQA/MQA 时，`n_kv_heads` 远小于注意力头数，这是长上下文能够落地的关键。

以 Llama 3 70B 为例（80 层、8 个 KV head、`head_dim=128`、FP16）：

```text
KV_per_token = 2 × 80 × 8 × 128 × 2
             = 327,680 B
             ≈ 320 KiB/token

128K 上下文、batch = 8:
327,680 × 131,072 × 8 = 343.6 GB ≈ 320 GiB
```

单条 128K 序列的 KV cache 约 42.95 GB（40 GiB），已经接近 70B BF16 权重（140 GB）的三分之一；batch = 8 时约 343.6 GB，超过权重本身。训练时通常不跨步保存 KV cache，但长上下文训练的激活值和注意力工作集会体现类似的增长，预算时不能只算权重。

## 3. 效率预算：MFU 与 HFU

**MFU（Model FLOPs Utilization）** 衡量“模型真正需要的 FLOPs”占硬件峰值的比例；**HFU（Hardware FLOPs Utilization）** 衡量“硬件实际执行的 FLOPs”占峰值的比例。

```text
MFU = model_FLOPs_per_s / (G · P_dense)
HFU = hardware_FLOPs_per_s / (G · P_dense)
HFU / MFU = hardware_FLOPs / model_FLOPs
```

- 分母必须是**稠密峰值**，且精度要与分子一致。H100 的 BF16 稠密峰值是 989 TFLOPS，稀疏峰值是 1,979 TFLOPS；用 1,979 做分母会把 MFU 系统性低估一半。
- 分子是模型 FLOPs 时得到 MFU；分子包含重计算、padding、注意力额外项等硬件 FLOPs 时得到 HFU。
- 因此 `HFU ≥ MFU`。全量重计算时硬件 FLOPs 是模型 FLOPs 的 `8/6 = 1.333` 倍，对应 `MFU = 0.75 × HFU`；选择性重计算的比例介于两者之间。
- PaLM 论文同时报告 46.2% MFU 和 57.8% HFU。两者比值 `57.8 / 46.2 ≈ 1.25`，说明硬件实际执行的 FLOPs 比模型 FLOPs 多约 25%，与选择性重计算和注意力开销的量级一致。**不能把 57.8% 当作 MFU 引用。**

| 模型/系统 | MFU | HFU | 口径说明 |
|-----------|-----|-----|---------|
| GPT-3 175B / 约 10,000 V100 | 约 21.3% | — | 6N + V100 稠密峰值 + 约 13.7 天假设的反推值 |
| PaLM 540B / 6,144 TPU v4 | 46.2% | 57.8% | 论文报告；HFU 含重计算等硬件 FLOPs |
| Llama 3 405B / 16,384 H100 | 38–43% | — | 论文公开范围 |

MFU 只有在同模型规模、同硬件、同精度、同 batch 策略下横比才有意义。小模型的 MFU 天然偏低，因为 kernel launch 和数据搬运占比更高。

## 4. 硬件预算推导流程

把前面的公式串起来，得到一条从 workload 到成本的预算链：

```text
workload: N, D, s, b, precision, epochs
  → FLOPs:        C = 6ND（全量重计算按 8ND 做硬件预算）
  → peak time:    T_peak = C / (G · P_dense)
  → MFU:          target 或 measured
  → actual time:  T_actual = T_peak / MFU
  → memory:       M_state/(TP·PP) + A_activations + KV + workspace
  → interconnect: B_req ≈ 2 · S_grad/(TP·PP) / T_step
  → power/energy: P_IT = G · TDP；P_facility = P_IT · PUE；E = P_facility · T
  → cost:         G · T · $/GPU-h + E · $/kWh + network/storage
```

| 步骤 | 关键输入 | 公式 | 输出 | 典型失败信号 |
|------|---------|------|------|-------------|
| 1. Workload | `N`、`D`、`s`、`b`、精度 | 无 | 计算/显存的基本规模 | 把总参数当激活参数、忘记 epoch |
| 2. FLOPs | 参数量、token 数 | `6ND` 或 `8ND` | 模型/硬件 FLOPs | 长上下文仍只用 6N |
| 3. Peak time | FLOPs、卡数、峰值 | `C / (G · P_dense)` | 理论下限 | 用稀疏峰值或混用精度 |
| 4. MFU | 实测或目标效率 | `T_actual = T_peak / MFU` | 实际时间 | 把 HFU 当 MFU |
| 5. Memory | 状态、激活、KV、workspace | 分项求和 | 每卡显存占用 | 只算权重、不算激活 |
| 6. Interconnect | 梯度大小、并行度、步时间 | `2S/(TP·PP)/T_step` | 每卡带宽需求 | 把双向带宽当单向 |
| 7. Power/energy | TDP、PUE、时间 | `P_IT · PUE · T` | MWh/GWh | 只算 GPU、不算机房 |
| 8. Cost | GPU-hours、电价、租用价 | 分项求和 | 总成本、$/token | 漏掉网络、存储、运维 |

### 4.1 Worked example：Llama 3 70B / 15T tokens

**假设**（示例配置，不是 Llama 3 70B 的实际训练集群）：

```text
N = 70e9, D = 15e12, L = 80, h = 8192, s = 8192
precision = BF16, micro-batch b = 4
G = 8,192 × H100 SXM（989 TFLOPS dense, 80 GB, 3.35 TB/s, 700 W）
TP = 8, PP = 8, DP = 128（8 × 8 × 128 = 8,192）
target MFU = 40%（Llama 3 405B 公开值 38–43% 的锚点）
PUE = 1.25, $2/GPU-h, $0.08/kWh
```

**第一步：算力与时间。**

```text
C_model = 6 × 70e9 × 15e12 = 6.3e24 FLOPs
C_hw    = 8 × 70e9 × 15e12 = 8.4e24 FLOPs      # 全量重计算口径

P_peak = 8,192 × 989e12 = 8.101e18 FLOP/s
T_peak = 6.3e24 / 8.101e18 = 7.78e5 s = 216 h = 9.0 d
T_40%  = 216 / 0.40 = 540 h = 22.5 d
```

**第二步：显存账本。** 16 B/参数下模型状态总量 `70e9 × 16 = 1.12 TB`；在 `TP×PP = 64` 路切分后，每卡约 17.5 GB。

| 项目 | 计算 | 每 GPU 结果 |
|------|------|------------|
| 模型状态（16 B） | `70e9 × 16 / 64` | 17.5 GB |
| 模型状态（12 B） | `70e9 × 12 / 64` | 13.1 GB |
| 模型状态（8 B） | `70e9 × 8 / 64` | 8.75 GB |
| 激活值（`c_act=34`） | `80 × 8192 × 4 × 8192 × 34 / 64` | 11.4 GB |
| 激活值（`c_act=20`，重计算） | 同式，`c_act=20` | 6.7 GB |
| workspace/通信缓冲 | 工程预留 | 5 GB |
| 合计（16 B，不重计算） | `17.5 + 11.4 + 5` | 33.9 GB |
| 合计（16 B，重计算） | `17.5 + 6.7 + 5` | 29.2 GB |

80 GB 的 H100 在这个配置下还剩约 46–51 GB 余量，显存不是主要瓶颈。若把 `TP×PP` 降到 32，模型状态翻倍到 35 GB，合计约 51–57 GB，仍然放得下但余量明显变小；若改用 12 B/8 B 口径，每卡分别再省约 4.4 GB/8.75 GB。注意这是“能放下”的账，不等于“跑得快”。

**第三步：互连带宽需求。** 设每步 token 数为 `DP × b × s`：

```text
D_step = 128 × 4 × 8192 = 4.194e6 tokens
C_step = 6 × 70e9 × 4.194e6 = 1.76e18 FLOPs
T_step = 1.76e18 / (8.101e18 × 0.40) = 0.543 s

S_grad  = 2 B × 70e9 = 140 GB
S_slice = 140 / (8 × 8) = 2.19 GB
V_AR    ≈ 2 × 2.19 × 127/128 = 4.34 GB/GPU/step
B_req   = 4.34 / 0.543 = 8.0 GB/s/GPU
```

每卡 IB NDR 单向约 50 GB/s，DP 梯度 All-Reduce 的净需求约 8 GB/s，占单端口约 16%，看起来余量充足。但实际还要叠加 PP 的激活传输、TP 的节点内通信、checkpoint 写盘和拥塞/慢节点，因此工程上通常按 2–3 倍余量规划，并做通信/计算重叠。

**第四步：功率、能量与成本。**

```text
P_IT   = 8,192 × 700 W = 5.73 MW
P_fac  = 5.73 × 1.25 = 7.17 MW
E      = 7.17 MW × 540 h = 3.87 GWh
E/token = 3.87e6 kWh × 3.6e6 J/kWh / 15e12 = 0.93 J/token

GPU-hours = 8,192 × 540 = 4.42e6
租金       = 4.42e6 × $2 = $8.85M
电费       = 3.87e6 kWh × $0.08 = $0.31M
$/token    ≈ $8.85M / 15e12 = $0.59 / 1M tokens
```

以上成本只含 GPU 租用和电费，不含网络、存储、运维和失败重跑；`$/GPU-h` 与电价都是示例假设，不构成采购或报价依据。

**第五步：敏感性。** MFU 从 40% 降到 35%，时间从 540 h 增到 617 h（25.7 天），租金从 $8.85M 增到 $10.1M；升到 45% 则降到 480 h（20.0 天）和 $7.86M。在这个配置下，结论是：**算力和时间是主约束，显存有余量，DP 梯度 All-Reduce 不是网络瓶颈**。如果序列长度从 8K 增到 32K，激活值和注意力的 `s²` 项会重新改写显存与算力账本；如果 MFU 从 40% 掉到 30%，时间与租金约增加 33%。

## 5. 口径卡

| 口径 | 正确定义 | 常见误用 |
|------|---------|---------|
| 6N vs 8N | 6N 是模型 FLOPs（前向 2N + 反向 4N）；8N 是全量重计算后的硬件 FLOPs | 用 8N 算 MFU 分子，或把 6N 当作硬件实际执行量 |
| 12 / 16 / 8 B | 每参数训练状态字节数：12 B 无 FP32 master，16 B 含 master，8 B 全 BF16/8-bit | 不说明口径就报“70B 要 560 GB/1.12 TB”；把模型状态和激活混在一起 |
| dense / sparse | 稠密峰值与 2:4 稀疏峰值通常差 2 倍 | MFU 分母用稀疏峰值；跨精度比较峰值 |
| MFU / HFU | MFU 用模型 FLOPs，HFU 用硬件 FLOPs；HFU ≥ MFU | 把 PaLM 的 57.8% HFU 写成 MFU；忽略重计算 |
| GB / GiB | GB = 10⁹ 字节，GiB = 2³⁰ 字节 | 把 343.6 GB 写成 343.6 GiB；厂商标称容量混用 |

## 6. 边界：哪些问题不在这篇展开

本篇只回答“需要多少算力、显存、带宽、电和钱”，是可行性与预算分析。它不回答“模型怎么切、通信怎么调、故障怎么恢复”。以下问题属于系统层，建议按顺序阅读 why-ai-cluster 的对应章节：

- 数据并行、张量并行、流水线并行的原理、通信量与组合方式：[数据并行 DP](https://github.com/zyfengaa/why-ai-cluster/blob/main/05-并行策略篇/01-数据并行DP.md)
- 给定模型和卡数后，TP/PP/DP 如何选型：[并行策略选型决策树](https://github.com/zyfengaa/why-ai-cluster/blob/main/05-并行策略篇/07-并行策略选型决策树.md)
- 通信为什么慢、NCCL 调优到底在调什么：[NCCL 调优到底在调什么](https://github.com/zyfengaa/why-ai-cluster/blob/main/08-运维观测篇/03-NCCL调优到底在调什么.md)

## 总结

训练系统的硬件预算可以压缩成一条链：`6ND → 峰值时间 → MFU → 实际时间 → 显存账本 → 带宽需求 → 能量与成本`。6N 是模型 FLOPs 的近似，长上下文、重计算和 MoE 都会让它偏离；12/16/8 B 是三种不同的训练状态口径，70B 分别对应 840 GB/1.12 TB/560 GB；MFU 和 HFU 的分子不同，PaLM 的 57.8% 不能当 MFU 用。把口径写在数字旁边，比把数字算到小数点后两位更重要。

## 参考文献

1. Brown, T. B., et al. "Language Models are Few-Shot Learners." *NeurIPS*, 2020. — GPT-3 的 175B 参数、300B token、约 10,000 张 V100 训练配置，以及 6N 案例的总 FLOPs 计算。
2. Kaplan, J., et al. "Scaling Laws for Neural Language Models." *arXiv:2001.08361*, 2020. — 6N 计算量近似与“计算量随参数量、token 数缩放”的原始讨论。
3. Chowdhery, A., et al. "PaLM: Scaling Language Modeling with Pathways." *JMLR*, 2022. — PaLM 540B 在 TPU v4 上的 46.2% MFU 与 57.8% HFU 口径。
4. Grattafiore, A., et al. "The Llama 3 Herd of Models." *arXiv:2407.21783*, 2024. — Llama 3 70B 的 15T token、80 层/8 KV head 架构，以及 405B 的 38–43% MFU 公开范围。
5. Rajbhandari, S., et al. "ZeRO: Memory Optimizations Toward Training Trillion Parameter Models." *SC*, 2020. — 16 B/参数训练状态的分解（权重、梯度、FP32 master、Adam m/v）。
6. Korthikanti, V., et al. "Reducing Activation Recomputation in Large Transformer Models." *arXiv:2205.05198*, 2022. — 激活值显存模型与选择性重计算，用于 `c_act` 与 8N 的边界说明。
7. Dao, T., et al. "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness." *NeurIPS*, 2022. — 注意力分数的分块计算，说明显式物化 `s²` 矩阵的显存代价。
8. NVIDIA. *H100 Tensor Core GPU Datasheet* and *Hopper Architecture Whitepaper*, 2022–2023. — H100 989 TFLOPS BF16 稠密峰值、80 GB HBM3、3.35 TB/s、700 W；与 `SPECS.md` §1/§6 一致。
