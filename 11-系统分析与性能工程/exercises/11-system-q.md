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

你正在训练一个 100B 参数的大语言模型，使用 1,024 个 NVIDIA H100 GPU。每张 H100 的规格：Peak 989 TFLOPS（FP16 Tensor Core），显存 80 GB HBM3，带宽 3.35 TB/s。

训练配置：
- 模型参数：100B（使用 BF16 精度）
- Token 总量：200B
- 优化器：AdamW（FP32 状态）
- 每 GPU batch size：4 个样本，每样本 4096 token
- 张量并行：8 路（节点内）
- 数据并行：64 路（跨节点）
- 流水线并行：2 路

### 问题要求

1. 计算总训练所需的 FLOPs。
2. 计算每张 GPU 的显存需求（包括模型状态和激活值），判断是否在 80 GB 限制内。
3. 假设 MFU 为 45%，估算理论训练时间（天）。
4. 如果发现实际 MFU 只有 30%，最可能的原因是什么？如何分析定位？
5. 提出至少三个系统层面的优化方案来提高 MFU。

### 参考答案

#### (1) 总 FLOPs

对于 Transformer 模型，每 Token 计算量 ≈ 6 × 参数量。
$$
\text{Total FLOPs} = 200 \times 10^9 \text{ tokens} \times 100 \times 10^9 \text{ params} \times 6 = 1.2 \times 10^{23} \text{ FLOPs}
$$

#### (2) 显存需求分析

**模型状态（使用 ZeRO-3）**：

每个 GPU 持有的分片（1,024 GPU）：
- 权重：100B × 2 bytes / 1024 ≈ 195 MB
- 梯度：100B × 2 bytes / 1024 ≈ 195 MB
- 优化器状态（FP32 Momentum + Variance）：100B × 8 bytes / 1024 ≈ 781 MB

模型状态合计：~1.17 GB/GPU —— ZeRO-3 下非常小

**激活值**：

每 GPU batch size = 4, 序列长度 = 4096, 隐藏维度（假设 8192）：
- 每层 attention：batch × seq_len × hidden_dim × 精度 × 层部分 = 4 × 4096 × 8192 × 2 bytes × 几个数组
- 粗略估计：每 GPU 激活值约 20-35 GB（取决于序列长度和是否使用 activation checkpointing）
- 如果使用 activation checkpointing（梯度检查点），激活值可以降低到约 8-12 GB（以额外 30% 计算开销为代价）

**其他**：通信缓冲区、临时变量等约 2-5 GB

**总显存估计**：
- 不使用 checkpointing：35 + 1.2 + 5 ≈ 41.2 GB （在 80 GB 内）
- 使用 checkpointing：10 + 1.2 + 5 ≈ 16.2 GB （非常充裕）

结论：**可以放进 80 GB 显存**，但如果不使用 checkpointing，剩余空间有限（~39 GB），可能限制 batch size 的扩展。建议使用梯度检查点技术来释放显存。

#### (3) 理论训练时间

假设 MFU = 45%：

理论峰值算力：1024 × 989 TFLOPS = 1,012,736 TFLOPS ≈ 1.01 × 10^18 FLOP/s

以 45% MFU 计，有效算力 = 1.01 × 10^18 × 0.45 = 4.55 × 10^17 FLOP/s

训练时间 = 1.2 × 10^23 / (4.55 × 10^17) ≈ 264,000 秒 ≈ 73.3 小时 ≈ **3.05 天**

#### (4) MFU 只有 30% 的原因分析和诊断

实际 MFU 只有 30%，远低于预期 45%，需要系统性地诊断：

**可能的根本原因分析**：

1. **通信瓶颈（最可能）**：在 1,024 个 GPU 上，All-Reduce 通信量随 GPU 数增长。数据并行度 64 路意味着每步 All-Reduce 在 64 个节点间进行。InfiniBand 带宽可能不足以支持这么大的通信量。诊断方法：使用 `nsys` 记录训练过程，检查 GPU 时间线中是否有大段的通信空闲时间。

2. **张量并行内通信开销**：8 路张量并行需要在每层内进行 2 次 All-Reduce（前向和反向），如果 NVLink 带宽被共享或存在拓扑问题，可能成为瓶颈。诊断方法：运行 ncu 检查单个 GPU 的 kernel 效率。

3. **流水线并行气泡**：2 路流水线并行的气泡比例约为 (P-1)/(P+M-1) 其中 P=2 是 stage 数，M 是 micro-batch 数。如果 M 小，气泡比例高。诊断方法：检查 TensorBoard trace viewer 中 GPU 的空闲时间比例。

4. **数据加载瓶颈**：CPU 预处理跟不上 GPU 计算速度。诊断方法：在 TensorBoard profiler 中查看输入管线分析，检查是否有大量 TPU/GPU 空闲等待数据的时间。

5. **显存不足导致的内存交换**：如果模型状态加上激活值接近或超过 80 GB，可能发生显存溢出，导致 CPU→GPU/GPU→CPU 的数据换入换出。诊断方法：检查 `nvidia-smi` 的显存使用情况。

**定位步骤**：

```
步骤 1: nsys profile → 检查时间线 → 看 GPU 利用率、kernel 密度、通信间隙
步骤 2: 如果 GPU 利用率低 → 检查数据传输重叠情况
步骤 3: 如果 GPU 利用率高但 MFU 低 → ncu 分析单个 GPU kernel 效率
步骤 4: 检查 All-Reduce 性能：使用 NCCL 的 ring 算法性能测试
步骤 5: 检查数据加载线程的 CPU 使用率（是否 CPU 侧过载）
```

#### (5) 提高 MFU 的优化方案

**方案 1：优化通信与计算重叠**

在反向传播中，利用梯度计算的异步性，将梯度 All-Reduce 与后续的反向传播计算重叠。具体实现：
- 使用 PyTorch 的 `torch.distributed.bucketized_allreduce` 或 DeepSpeed 的 gradient partitioning
- 当计算出一个层的梯度时，立即开始该层梯度的 All-Reduce，不需要等待所有层完成
- 预期收益：MFU 提升 5-15%

**方案 2：选择合适的并行策略**

当前配置（TP=8, DP=64, PP=2）可能不是最优组合。对于 1,024 GPU 和 100B 模型：
- 考虑增加 PP 到 8（减少 DP 到 16），减少跨节点 All-Reduce 规模
- 或使用 ZeRO-3 替代数据并行，消除 DP 的 All-Reduce，改用更高效的 gather/scatter 通信
- 预期收益：MFU 提升 3-10%

**方案 3：增大 micro-batch 数量减少流水线气泡**

在流水线并行中，增加每个 GPU 的 micro-batch 数量可以减少气泡占比。如果每 GPU batch size = 4 且 M=4，气泡约为 (P-1)/(P+M-1) = 1/5 = 20%。增加 M 到 8 可将气泡降至 1/9 ≈ 11%。注意这需要足够显存来存放更多激活值，因此可以使用梯度检查点来平衡。

**方案 4：使用 Flash Attention 优化注意力计算**

Transformer 中的注意力计算（QK^T softmax 和 PV 计算）的内存访问量为 O(N²)，是常见的瓶颈。使用 Flash Attention（Dao et al., 2022）通过 tiling 技术将注意力计算的内存访问量从 O(N²) 降低到 O(N)，显著减少 HBM 访问。
- 预期收益：约 10-20% 的每步时间减少

**方案 5：使用 8-bit 优化器状态**

使用 8-bit Adam（bitsandbytes 库）将优化器状态从 FP32（8 bytes/参数）降低到 INT8（1 byte/参数），减少显存占用和通信量。显存释放后可用于更大的 batch size 或更大的 micro-batch 数。
- 预期收益：显存节省 3/4 的优化器状态，可间接提升 MFU 约 3-8%

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
