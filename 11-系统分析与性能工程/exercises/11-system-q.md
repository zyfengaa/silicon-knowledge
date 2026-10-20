# 系统分析与性能工程 习题

> 本习题涵盖 Roofline 模型分析、Amdahl 加速比计算、perf stat 输出解读和大模型训练瓶颈分析五大主题。

---

## 问题一：算术强度计算

### 问题描述

考虑一个 FP32 精度的向量操作 `z = a * x + y + b`（其中 a 和 b 是标量常数，x, y, z 是长度为 N 的向量）。请计算：

1. 这个操作的算术强度（Arithmetic Intensity, FLOP/Byte）。
2. 如果系统硬件参数为：Peak GFLOPS = 2,000 GFLOPS，Peak Bandwidth = 200 GB/s，这个操作是 compute-bound 还是 memory-bound？
3. 可达到的性能（Attainable GFLOPS）是多少？
4. N 增大到多少时这个操作会从 memory-bound 变为 compute-bound？（提示：算术强度不依赖 N，但总执行时间和计算/访存的绝对时间会有变化——实际上算术强度与 N 无关，所以请解释为什么 N 改变不会改变 bound type）

### 参考答案

#### (1) 算术强度计算

每轮迭代的计算：
- 1 次乘法 (a × x[i])
- 2 次加法 (a×x[i] + y[i] + b)
- 总计：3 FLOP（或者 2 FLOP，如果编译器将 a×x+b 优化为 FMA？严格来说乘法和加法不能合并为 FMA，因为中间结果 a×x + y 后才加 b，所以是 3 FLOP）

每轮迭代的数据搬运（FP32）：
- 读 x[i]: 4 Bytes
- 读 y[i]: 4 Bytes
- 写 z[i]: 4 Bytes
- 总计：12 Bytes

算术强度 AI = 3 FLOP / 12 Bytes = 0.25 FLOP/Byte

（如果将 a×x+y 视为融合乘加 FMA 计 2 FLOP，则 AI = 2/12 ≈ 0.167 FLOP/Byte，取决于编译器优化。这里以 3 FLOP 计算。）

#### (2) Bound 类型判断

脊点 Ridge AI = 2000 / 200 = 10 FLOP/Byte

AI = 0.25 << 10，SAXPY+BIAS 操作远在脊点左侧，是 **memory-bound**。

#### (3) 可达到性能

Attainable GFLOPS = AI × Peak BW = 0.25 × 200 = 50 GFLOPS

这只达到峰值计算能力的 50/2000 = 2.5%。

#### (4) N 增大与 bound type 的关系

算术强度 AI = (3 FLOP) / (12 Bytes) 与 N 无关。无论 N 取多大，每个元素的计算和访存比例保持不变。因此 N 的改变不会改变 bound type——只要 AI < Ridge，就是 memory-bound。

但实际上，当 N 非常小（如 N=1）时，缓存效果可能改变有效数据搬运量（数据可能在缓存中命中），但理论上如果数据必须从 DRAM 读取，则 AI 不变。

---

## 问题二：Roofline 分析——计算还是内存受限？

### 问题描述

给定一个 Roofline 模型和以下三个 kernel 的指标，请分析每个 kernel 的瓶颈并给出优化建议。

```
硬件参数：
  Peak GFLOPS: 3,000 (FP32)
  Peak BW: 750 GB/s

Kernel A:
  Arithmetic Intensity: 0.5 FLOP/Byte
  Achieved GFLOPS: 350

Kernel B:
  Arithmetic Intensity: 15 FLOP/Byte
  Achieved GFLOPS: 2,100

Kernel C:
  Arithmetic Intensity: 4 FLOP/Byte
  Achieved GFLOPS: 2,800
```

对于每个 kernel，回答：
1. 它是 compute-bound 还是 memory-bound？
2. 性能与理论天花板的差距是多少？（Achieved / Ceiling）
3. 优化建议是什么？
4. 对于 Kernel C，它的行为看似矛盾——算术强度为 4 却能达到 2,800。请解释为什么会发生这种情况。

### 参考答案

**脊点计算**：Ridge = 3000 / 750 = 4 FLOP/Byte

#### Kernel A: AI = 0.5

1. **Bound type**: AI (0.5) < Ridge (4) → **memory-bound**
2. **天花板差距**: 内存天花板 = 0.5 × 750 = 375 GFLOPS。实际性能 350 GFLOPS，效率 = 350/375 = 93.3%。说明内存带宽利用率很高。
3. **优化建议**：已经是 memory-bound，且带宽利用率 93.3%，进一步优化空间有限。可以考虑：
   - 使用计算和数据搬运重叠技术（double buffering）
   - 如果可以增加算术强度（如融合多个 kernel），可能将部分计算移到 compute-bound 区域
   - 考虑使用更高带宽的内存系统（如 HBM）
4. **问题 4 不适用**。

#### Kernel B: AI = 15

1. **Bound type**: AI (15) > Ridge (4) → **compute-bound**
2. **天花板差距**: 计算天花板 = 3000 GFLOPS。实际性能 2100 GFLOPS，效率 = 2100/3000 = 70%。
3. **优化建议**：计算效率 70%，还有优化空间：
   - 检查是否充分利用了 SIMD/向量化指令
   - 检查是否有数据依赖导致流水线停顿
   - 尝试循环展开（loop unrolling）提高指令级并行
   - 考虑使用更低精度的运算（如 FP16/BF16）利用 Tensor Core
   - 检查内存访问是否完全合并（coalesced），虽然它是 compute-bound，但非合并访问仍可能降低有效计算速度
4. **问题 4 不适用**。

#### Kernel C: AI = 4

1. **Bound type**: AI (4) 恰好等于 Ridge (4)。从理论上说，它位于脊点上，计算天花板和内存天花板相等。
2. **天花板差距**: 两个天花板都是 3000 GFLOPS。实际 2800 GFLOPS，效率 93.3%。
3. **优化建议**：效率已很高。可以优化使其进一步落入 compute-bound 区域（增加算术强度），或保持现状。
4. **解释**：AI = 4 恰好等于脊点，此时计算和内存理论上限相等。但实际中，由于缓存局部性和动态变化，一个 kernel 可能在某些时间段是 memory-bound、在其他时间段是 compute-bound。实测达到 2800 GFLOPS（93.3% 峰值）是非常好的性能，说明该 kernel 的优化已经很到位，算术强度也恰好处于平衡点。

---

## 问题三：Amdahl 加速比计算

### 问题描述

假设你将一个程序的 96% 实现了并行化（即并行比例 P = 0.96），剩余 4% 必须串行执行。

1. 计算在 4 核、16 核、64 核、256 核上的加速比（使用 Amdahl's Law）。
2. 最大可能的加速比是多少（核心数趋于无穷）？
3. 如果通过进一步优化，你将并行比例从 96% 提高到 99.5%，在 64 核上的加速比提升多少？
4. 请使用 Gustafson's Law 重新计算，假设并行部分随核心数线性扩展（弱扩展）。对于 64 核，Gustafson 加速比是多少？为什么与 Amdahl 的结果不同？
5. 实际中，为什么很难达到理论 Amdahl 加速比？

### 参考答案

#### (1) Amdahl 加速比计算

Amdahl's Law: S(N) = 1 / ((1-P) + P/N), P = 0.96

```
N = 4:    S = 1 / (0.04 + 0.96/4) = 1 / (0.04 + 0.24) = 1 / 0.28 ≈ 3.57×
N = 16:   S = 1 / (0.04 + 0.96/16) = 1 / (0.04 + 0.06) = 1 / 0.10 = 10.0×
N = 64:   S = 1 / (0.04 + 0.96/64) = 1 / (0.04 + 0.015) = 1 / 0.055 ≈ 18.2×
N = 256:  S = 1 / (0.04 + 0.96/256) = 1 / (0.04 + 0.00375) = 1 / 0.04375 ≈ 22.9×
```

#### (2) 最大加速比

S_max = 1 / (1-P) = 1 / 0.04 = 25×

即使有无穷多个核心，加速上限也只有 25 倍。那 4% 的串行部分决定了天花板。

#### (3) 优化后的加速比对比

P 从 0.96 提高到 0.995，在 64 核上：

原：S(64) = 1 / (0.04 + 0.96/64) = 18.2×
新：S(64) = 1 / (0.005 + 0.995/64) = 1 / (0.005 + 0.01555) = 1 / 0.02055 ≈ 48.7×

加速比提升：从 18.2× 到 48.7×，提升了 2.67 倍。

注意：将串行部分从 4% 降低到 0.5% 是非常困难的——往往需要改变算法或数据结构。这体现了 Amdahl 定律的"diminishing returns"特性：最初的优化（从 50% 到 96%）比最后的优化（从 96% 到 99.5%）更容易获得加速。

#### (4) Gustafson's Law 对比

Gustafson's Law: S(N) = P + (1-P) × N = N - α(N-1)，其中 α = 串行比例

取 α = 0.04（串行 4%）：
S(64) = 64 - 0.04 × (64-1) = 64 - 2.52 = 61.48×

Gustafson 加速比 61.48× 远超 Amdahl 的 18.2×。原因在于两者的假设不同：
- **Amdahl**：固定问题规模。64 核上计算能力增加了 64 倍，但串行部分 4% 限制了上限。
- **Gustafson**：固定执行时间。64 核上的问题规模可以扩大到原来的 61.48 倍，串行部分在扩展后的问题中所占比例极小。

两者都是正确的，回答的是不同问题——Amdahl 回答"固定问题要多快"，Gustafson 回答"固定时间能做多大"。

#### (5) 实际中难达到理论 Amdahl 加速比的原因

1. **通信开销**：Amdahl 模型没有考虑并行化引入的通信开销。随着核心数增加，通信时间通常超线性增长（All-Reduce 的延迟随核心数增长）。
2. **负载不均**：实际中难以完美平分工作，总有一些核心比其他核心先完成并等待。
3. **同步开销**：锁、屏障（barrier）等同步机制引入额外延迟。
4. **资源竞争**：核心之间竞争共享资源（L3 缓存、内存控制器、内存带宽），导致实际性能低于理论值。
5. **并行化开销**：创建线程/进程、分配任务等操作本身需要时间。

考虑通信开销后的修正 Amdahl 公式：S(N) = 1 / ((1-P) + P/N + O(N))，其中 O(N) 随核心数增长。当 N 很大时，O(N) 可能成为主要瓶颈。

---

## 问题四：perf stat 输出解读

### 问题描述

你运行一个科学计算程序，得到以下 perf stat 输出：

```
$ perf stat ./scientific_sim

 Performance counter stats for './scientific_sim':

         48,234.56  msec task-clock                #    1.000 CPUs utilized
    142,567,890,123  cycles                        #    2.956 GHz
    128,310,112,345  instructions                  #    0.90  insn per cycle
     78,912,345,678  cache-references              # 1635.627 M/sec
     23,456,789,012  cache-misses                  #   29.73% of all cache refs
     34,567,890,123  branches                      #  716.569 M/sec
      3,456,789,012  branch-misses                 #   10.00% of all branches

      48.234561789 seconds time elapsed
```

1. 计算 CPI（Cycles Per Instruction）和 IPC。
2. 该程序的缓存行为如何？是否存在缓存问题？
3. 分支预测的性能如何？是否构成瓶颈？
4. 如果该程序在具有 4,000 GFLOPS 峰值算力和 500 GB/s 峰值带宽的系统上运行，且已知算术强度约为 1.2 FLOP/Byte，该程序是 compute-bound 还是 memory-bound？
5. 综合以上所有指标，给出至少三条具体的优化建议。

### 参考答案

#### (1) CPI 和 IPC

IPC = 指令数 / 周期数 = 128,310,112,345 / 142,567,890,123 ≈ 0.90

CPI = 1 / IPC = 1 / 0.90 ≈ 1.11 cycles/instruction

IPC = 0.90 低于 1.0，说明 CPU 在每个周期中平均执行不到一条指令，存在显著的性能损失（流水线停顿）。

#### (2) 缓存行为分析

缓存未命中率 = 29.73%

这是一个非常高的缓存未命中率。通常 L3 缓存未命中率在 5% 以下算健康，超过 10% 就值得关注，而 29.73% 说明大量数据访问不得不去 DRAM。这会导致严重的性能损失，因为 DRAM 延迟（~100ns）远高于 L3 缓存（~40 cycles ≈ 13ns at 3GHz）。

可能的原因：
- 数据集太大，无法放入 L3 缓存
- 数据访问模式不友好（随机访问、大步长 stride、pointer chasing）
- 缺乏数据局部性优化（没有使用循环分块）

#### (3) 分支预测分析

分支误预测率 = 10.00%

10% 的误预测率非常高。现代 CPU 的分支预测器通常能达到 95-99% 的准确率（即误预测率 1-5%）。10% 意味着分支模式高度不规则，分支预测器无法有效工作。

每个分支误预测会导致流水线清空（flush），损失约 10-20 个周期的执行时间。分支误预测的总损失：
- 总分支数：34,567,890,123
- 误预测数：3,456,789,012
- 总损失（以 15 cycles/误预测计）：约 51.8 亿周期
- 占总周期比例：51.8B / 142.6B ≈ 36%

也就是说，分支误预测可能贡献了超过三分之一的执行时间！这是一个严重的性能瓶颈。

#### (4) Roofline 分析

脊点 AI = 4000 / 500 = 8 FLOP/Byte

程序 AI = 1.2 << 8，因此是 **memory-bound**。

这意味着即使 CPU 的计算能力翻倍，这个程序的性能也不会提升——瓶颈在内存带宽。缓存未命中率高（29.73%）进一步印证了这一结论：大量数据从 DRAM 读取，受限于内存带宽。

#### (5) 优化建议

1. **优化数据局部性，降低缓存未命中率**：使用循环分块（loop tiling / cache blocking）技术，使数据在计算期间尽可能驻留在 L2/L3 缓存中。例如，将矩阵运算分解为多个子块，每个子块大小适合缓存容量。

2. **降低分支误预测率**：
   - 对于循环中的条件判断，尝试使用**谓词执行（predication）** 替代分支（如使用 cmov 指令）
   - 重写热点代码，将数据驱动的分支模式改为查表（lookup table）
   - 对数据排序，使同一分支方向的数据集中在一起
   - 如果可能，用数学函数替代条件分支（如使用 max(a,0) 替代 if(a<0)）

3. **增加算术强度**：当前 AI = 1.2，远低于脊点的 8。通过融合多个 kernel（kernel fusion），将多个操作合并为一次内存访问，增加每字节数据的 FLOP 数。例如，将多个逐元素操作（如 mul、add、sigmoid）融合为一个 kernel。

4. **使用 prefetching 指令**：在程序无法避免不规则访存时，显式插入 prefetch 指令，让硬件提前将数据加载到缓存中，减少等待延迟。

---

## 问题五：大模型训练瓶颈分析

### 问题描述

你计划从零预训练一个 100B 参数的稠密 Transformer，训练 200B token，矩阵乘使用 BF16。候选硬件如下：

| 项目 | H100 SXM | B200 |
|------|----------|------|
| BF16 稠密峰值 | 989 TFLOPS | 2,250 TFLOPS |
| 显存 | 80 GB HBM3 | 192 GB HBM3e |
| 显存带宽 | 3.35 TB/s | 8 TB/s |
| TDP | 700 W | 1,000 W |

候选集群：

- 集群 A：1,024 × H100 SXM；
- 集群 B：512 × B200。

假设两套集群都能达到 45% MFU，暂不考虑故障、checkpoint 和通信重叠。显存估算采用 TP=8、PP=4（TP×PP=32），每卡激活值约 15 GB，workspace 与通信缓冲 5 GB。成本按 $2/H100 GPU-h、$3.5/B200 GPU-h 计，PUE=1.25，电价 $0.08/kWh。

### 问题要求

1. 计算总模型 FLOPs（6N）。若使用全量 activation recomputation，硬件 FLOPs 是多少？说明 MFU 与 HFU 的关系。
2. 分别按 16/12/8 B/参数计算模型状态总量和每卡占用；两种硬件的显存是否放得下？
3. 计算两套集群的理论最短训练时间和 45% MFU 下的实际时间（天），哪套更快？
4. 计算两套集群的 GPU-hours、GPU 租用成本、机房能耗（MWh）和 $/token，哪套更便宜？
5. 如果集群 A 实测 MFU 只有 30%，给出三步定位思路和每一步的预期观察。
6. 系统层扩展题（选做）：集群 A 的 DP 度是多少？BF16 梯度下每卡每步的 All-Reduce 通信量约多少？按第 3 问的 45% MFU，并假设 micro-batch=2、seq=4096，估算步时间和每卡网络带宽需求，并与 50 GB/s 的 IB NDR 单端口比较。并行策略与通信诊断的完整方法见 why-ai-cluster 的[数据并行 DP](https://github.com/zyfengaa/why-ai-cluster/blob/main/05-并行策略篇/01-数据并行DP.md)和[并行策略选型决策树](https://github.com/zyfengaa/why-ai-cluster/blob/main/05-并行策略篇/07-并行策略选型决策树.md)。

### 参考答案

#### (1) 总 FLOPs 与 MFU/HFU

```text
C_model = 6 × 100e9 × 200e9 = 1.2e23 FLOPs
C_hw    = 8 × 100e9 × 200e9 = 1.6e23 FLOPs   # 全量重计算
```

6N 是前向 2N + 反向 4N 的模型 FLOPs；全量重计算多跑一遍前向，硬件 FLOPs 变成 8N。两者关系：

```text
MFU = model_FLOPs_per_s / (G × dense_peak)
HFU = hardware_FLOPs_per_s / (G × dense_peak)
HFU / MFU = 8/6 = 1.333
MFU = 0.75 × HFU
```

若报告 HFU=45%，对应的 MFU 约为 33.75%；反之，若目标是 45% MFU，硬件侧实际可达到约 60% HFU。计算 MFU 时分母必须用稠密峰值，不能用 B200 的稀疏值。

#### (2) 模型状态与显存

模型状态总量：

```text
16 B/参数: 100e9 × 16 = 1.6e12 B = 1.6 TB
12 B/参数: 100e9 × 12 = 1.2e12 B = 1.2 TB
8 B/参数:  100e9 × 8  = 0.8e12 B = 0.8 TB
```

在 `TP×PP=32` 下，每卡模型状态为总量除以 32：

| 口径 | 总量 | 每卡模型状态 | + 激活/workspace | H100 80 GB | B200 192 GB |
|------|------|-------------|------------------|------------|-------------|
| 16 B | 1.6 TB | 50 GB | 70 GB | 放得下，但仅剩约 10 GB | 放得下 |
| 12 B | 1.2 TB | 37.5 GB | 57.5 GB | 放得下 | 放得下 |
| 8 B | 0.8 TB | 25 GB | 45 GB | 放得下 | 放得下 |

16 B 口径下 H100 的 70 GB 已经比较紧张：框架开销、碎片和通信 buffer 都可能把余量吃掉，实际训练通常要用 activation checkpointing、更多 PP 或更激进的状态分片。B200 的 192 GB 则没有这个问题。这里只算模型状态，DP 会复制状态；若用 ZeRO/FSDP，分布方式会变，但总量不变。

#### (3) 理论时间与实际时间

```text
集群 A 峰值 = 1,024 × 989e12 = 1.0127e18 FLOP/s
T_peak,A = 1.2e23 / 1.0127e18 = 1.185e5 s = 32.9 h = 1.37 d
T_45,A   = 32.9 / 0.45 = 73.1 h = 3.05 d

集群 B 峰值 = 512 × 2,250e12 = 1.152e18 FLOP/s
T_peak,B = 1.2e23 / 1.152e18 = 1.0417e5 s = 28.9 h = 1.21 d
T_45,B   = 28.9 / 0.45 = 64.3 h = 2.68 d
```

集群 B 快约 `73.1 / 64.3 ≈ 1.14×`，即少约 13.7% 的时间。两者峰值比 `1.152 / 1.0127 ≈ 1.137`，在 MFU 相同的前提下，时间比正好等于峰值比。

#### (4) 成本与能耗

```text
集群 A:
GPU-hours = 1,024 × 73.1 = 74,854
租金       = 74,854 × $2 = $149,708

P_IT  = 1,024 × 700 W = 716.8 kW
P_fac = 716.8 × 1.25 = 896 kW
E     = 896 kW × 73.1 h = 65,498 kWh ≈ 65.5 MWh
电费   = 65,498 × $0.08 ≈ $5,240

集群 B:
GPU-hours = 512 × 64.3 = 32,922
租金       = 32,922 × $3.5 = $115,227

P_IT  = 512 × 1,000 W = 512 kW
P_fac = 512 × 1.25 = 640 kW
E     = 640 kW × 64.3 h = 41,152 kWh ≈ 41.2 MWh
电费   = 41,152 × $0.08 ≈ $3,292
```

`$/token`：

```text
A: $149,708 / 200e9 = $7.49e-7/token ≈ $0.75 / 1M tokens
B: $115,227 / 200e9 = $5.76e-7/token ≈ $0.58 / 1M tokens
```

按给定租用价，集群 B 便宜约 23%。B200 的盈亏平衡单价约为 `$149,708 / 32,922 ≈ $4.55/GPU-h`：只要 B200 单价低于约 $4.55，B 的租金就更低；高于这个值，A 更便宜。电费相对 GPU 租金是小头，但在更大规模或更长训练中会变得可观。以上不含网络、存储、运维和失败重跑，属于示例假设，不构成采购依据。

#### (5) MFU 只有 30% 的三步定位

先算影响：`T_actual = 32.9 / 0.30 ≈ 109.7 h ≈ 4.57 d`，比 45% 时多约 50%。

1. **看时间线，先分清“等”还是“算得慢”**：用 `nsys`/DCGM 看每步的 GPU 活跃区间。若空档出现在 All-Reduce、PP 边界或 step 同步处，优先怀疑通信、同步或负载不均；若空档出现在 batch 开始处且 CPU/IO 很高，优先怀疑数据加载。
2. **做单卡/单节点微基准**：用 `ncu` 跑同一模型的 GEMM/attention kernel，检查 Tensor Core 利用率、HBM 吞吐和 occupancy。若单卡也达不到预期，问题在 kernel 或模型实现；若单卡正常而集群低，问题在扩展性、通信或慢节点。
3. **检查并行配置与网络**：PP=4 的气泡比例约为 `(PP-1)/(PP-1+M)`（M 为 micro-batch 数），TP=8 走节点内 NVLink，DP 走跨节点网络；用 `nccl-tests` 看 busbw 是否接近端口规格，用 `NCCL_DEBUG=INFO` 和慢节点检测确认是否有掉队 rank。完整的 NCCL 调优方法见 why-ai-cluster 的 [NCCL 调优到底在调什么](https://github.com/zyfengaa/why-ai-cluster/blob/main/08-运维观测篇/03-NCCL调优到底在调什么.md)。

预期观察：通信受限时，step 时间随 DP 增大而上升，通信窗口明显；PP 气泡表现为流水线边界周期性空闲；数据受限表现为 GPU 等 batch；kernel 受限则单卡微基准也低。

#### (6) 系统层扩展题

集群 A 的 DP 度：

```text
DP = 1,024 / (TP × PP) = 1,024 / 32 = 32
```

BF16 梯度总量为 `2 B × 100e9 = 200 GB`。每个 GPU 只持有 `1/(TP×PP)` 的梯度切片，因此：

```text
S_slice = 200 GB / 32 = 6.25 GB
V_AR ≈ 2 × 6.25 × (32-1)/32 = 12.1 GB/GPU/step
```

取每步 global batch = `DP × micro-batch × seq = 32 × 2 × 4096 = 262,144` token，则：

```text
C_step = 6 × 100e9 × 262,144 = 1.57e17 FLOPs
T_step = 1.57e17 / (1.0127e18 × 0.45) ≈ 0.345 s
B_req  = 12.1 GB / 0.345 s ≈ 35 GB/s/GPU
```

50 GB/s 的 IB NDR 单端口理论上够用，但带宽占用已到约 70%，再叠加 PP 激活传输、TP 通信、checkpoint 写盘和拥塞，实际很容易掉到 35 GB/s 以下。此时通信开始吞掉计算时间，MFU 会从 45% 下滑。工程上要么降低 DP/增大 PP、要么增大 global batch 拉长 step 时间、要么做通信/计算重叠；具体选型见 why-ai-cluster 的[并行策略选型决策树](https://github.com/zyfengaa/why-ai-cluster/blob/main/05-并行策略篇/07-并行策略选型决策树.md)。本题只做一阶估算，不含协议开销和集合通信算法差异。

---

## 参考文献

1. Williams, S., Waterman, A., & Patterson, D. "Roofline: An Insightful Visual Performance Model for Multicore Architectures." *Communications of the ACM*, 52(4), 2009.
2. Amdahl, G. M. "Validity of the Single Processor Approach to Achieving Large-Scale Computing Capabilities." *AFIPS Spring Joint Computer Conference*, 1967.
3. Gustafson, J. L. "Reevaluating Amdahl's Law." *Communications of the ACM*, 31(5), 1988.
4. Gregg, B. *Systems Performance: Enterprise and the Cloud*. 2nd Edition, Addison-Wesley, 2020.
5. Rajbhandari, S., et al. "ZeRO: Memory Optimizations Toward Training Trillion Parameter Models." *SC'20*, 2020.
6. Narayanan, D., et al. "Efficient Large-Scale Language Model Training on GPU Clusters Using Megatron-LM." *SC'21*, 2021.
7. Dao, T., et al. "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness." *NeurIPS'22*, 2022.
8. Dettmers, T., et al. "8-bit Adam: An Optimizer for Training Neural Networks with Almost No Memory Overhead." *NeurIPS'22*, 2022.
