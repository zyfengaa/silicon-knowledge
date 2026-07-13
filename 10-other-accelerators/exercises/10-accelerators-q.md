# Module 10: Other Accelerators — Exercises

## Questions

### Question 1: FPGA Design Philosophy

FPGA 和 CPU/GPU 的本质区别是什么？请从以下维度分析：

a) 执行模型（指令驱动 vs. 数据流）
b) 控制开销的来源和影响
c) 时钟频率差异的原因

### Question 2: FPGA vs. GPU — Scenario Selection

对于以下场景，请判断选择 FPGA 还是 GPU 更合适，并说明理由：

a) 100 Gbps 网络数据包的实时解析和过滤
b) ResNet-152 的大批量（batch=1024）推理部署
c) 高频交易中的超低延迟价格预测（端到端延迟 < 5μs）
d) 训练一个 70B 参数的语言模型

### Question 3: Wafer-Scale vs. Distributed

Cerebras WSE 采用整晶圆方案，而 NVIDIA 使用多 GPU 集群方案。

a) Cerebras 为什么认为"不在多个芯片间切分模型"是有益的？列出至少 3 个优点。
b) 相比 GPU 集群，WSE 的劣势是什么？
c) 如果模型参数（175B）远超 WSE 的片上 SRAM（40GB），Cerebras 应该怎么办？

### Question 4: Near-Memory Computing Motivation

考虑以下代码：

```python
# 向量加法
def saxpy(a, x, y, n):
    for i in range(n):
        y[i] = a * x[i] + y[i]
```

a) 请分析这个操作在传统 Von Neumann 架构中的瓶颈。为什么它是"memory-bound"的？
b) 解释 Samsung HBM-PIM 如何加速这种操作。具体是哪个硬件环节被改善了？
c) 假设一个程序的计算密集型远高于访存密集型（如大型矩阵乘法），PIM 是否能带来收益？为什么？

---

## Answers

### Answer 1: FPGA Design Philosophy

**a) 执行模型**

| 维度 | CPU/GPU | FPGA |
|------|---------|------|
| 执行方式 | 从内存读取指令 → 译码 → 执行 | 硬件电路直接执行，无指令取指/译码 |
| 控制流 | PC 寄存器、分支预测、异常处理 | 硬件状态机或纯组合逻辑 |
| 并行度获得方式 | 多核 / 多线程 / SIMD | 流水线级和空间并行（复制硬件） |
| 灵活性 | 运行时指令可变 | 运行时电路固定，重构需加载新位流 |

**b) 控制开销**

- CPU 每周期有 ~5-15% 功耗用于取指/译码，额外的功耗用于 OOO（乱序执行）、分支预测、缓存一致性
- GPU 有 warp 调度器、共享资源管理开销
- FPGA 的控制路径开销为零——"电路就是控制"

**c) 频率差异**

- FPGA 使用可编程互联（SRAM 控制的 pass transistor），信号经过更多开关和导线，RC 延迟大
- CPU/GPU 使用金属定制的互联，RC 延迟小，可支持更高频率
- FPGA 的 LUT 引入了多级逻辑延迟，而 ASIC 的标准单元库经过专门优化

### Answer 2: FPGA vs. GPU — Scenario Selection

**a) 100 Gbps 网络包处理 → FPGA**

原因：线速处理要求每个包在纳秒级完成处理。GPU 的 kernel 启动延迟（~10μs）和批处理模式不适合这种实时流处理。FPGA 可以创建全流水线的包处理管道，延迟仅数百纳秒。

**b) ResNet-152 大批量推理 → GPU**

原因：大批量推理可以充分利用 GPU 的 Tensor Core，实现极高的吞吐量。FPGA 的峰值 FLOPS 远低于 GPU（4.2 vs 19.5 TFLOPS），在大批量下效率不如 GPU。

**c) 超低延迟推理 → FPGA**

原因：端到端延迟需求 < 5μs 排除了 GPU（kernel 启动延迟 ~10-50μs）。FPGA 可以将推理模型实现为固定延迟的流水线，延迟可稳定在 1-2μs 以内。

**d) 训练 70B 语言模型 → GPU**

原因：训练需要高精度浮点（FP32/BF16），大量矩阵乘法，以及成熟的分布式训练框架（FSDP, Megatron-LM）。GPU 在峰值算力、软件生态和分布式系统支持上全面优于 FPGA。

### Answer 3: Wafer-Scale vs. Distributed

**a) WSE 的优点**

1. **完全消除片间通信**：所有核心在同一芯片上，通信延迟 < 1ns，无需处理 all-reduce 等集合通信
2. **超高片上带宽**：20 PB/s，远高于任何片外互联
3. **简化编程模型**：不需要数据并行、模型并行、流水线并行等复杂策略
4. **确定性调试**：不存在分布式系统的异步性和一致性难题

**b) WSE 的劣势**

1. **单芯片算力上限**：~400 TFLOPS，远低于大型 GPU 集群（上万 GPU 可达 EFLOPS）
2. **成本**：定制晶圆、水冷、封装导致单系统成本极高
3. **容量限制**：40GB 片上 SRAM 无法容纳 GPT-3 175B 模型
4. **软件生态**：远不如 CUDA，缺乏第三方库支持

**c) 超出 SRAM 容量时的方案**

1. 多 CS-2 系统集群：将模型切分到多个 Cerebras 系统（模型并行 + 数据并行）
2. 使用 ZeRO 技术：将优化器状态等分布到多个系统
3. 接受更大延迟：将部分层的数据放到外部 DRAM（但 Cortex 设计为优先使用 SRAM）

但这样一来，原来"单芯片无通信"的核心优势就会减弱。

### Answer 4: Near-Memory Computing Motivation

**a) SAXPY 的瓶颈**

SAXPY（y = a·x + y）的算术强度为：

```
每轮迭代:
- 2 个读取 (x[i], y[i]) + 1 个写入 (y[i]) = 3 × 4 bytes = 12 bytes
- 2 个操作 (乘 + 加) = 2 FLOPS

算术强度 AI = 2 FLOPS / 12 Bytes ≈ 0.17 FLOP/Byte

典型系统:
- CPU 峰值: ~200 GFLOPS
- 内存带宽: ~40 GB/s
- Ridge Point = 200 / 40 = 5 FLOP/Byte

AI (0.17) << Ridge Point (5) → 强烈 memory-bound
处理器大部分时间在等待数据，利用率极低 (~3%)
```

**b) HBM-PIM 的改善**

HBM-PIM 在每个 DRAM bank 添加了一个 8-bit ALU。SAXPY 的执行变为：

```
传统:
CPU 发出 load 指令 → 数据通过总线传到 CPU → 计算 → 写回 DRAM

HBM-PIM:
CPU 向 PIM bank 发送 "执行 SAXPY" 命令
PIM bank 内:
  Bank 行缓冲 → PCU (ALU) → 写回行缓冲
  数据在 DRAM bank 内部完成计算，不经过片外总线

改善的关键环节:
1. 消除数据搬运能耗（~180 pJ/word 的 DRAM 访问能耗节省）
2. 释放片外总线带宽
3. 提高内存带宽利用率（从 10-30% 到 70-90%）
```

**c) 计算密集型程序的收益**

对于计算密集型程序（如大矩阵乘法，AI > 10），PIM 的收益有限甚至为负：

1. AI > Ridge Point → 程序已经是 compute-bound，瓶颈在处理器算力，不在内存带宽
2. PIM 中的 ALU 远弱于 CPU/GPU 的 ALU（DRAM 工艺限制），计算性能更低
3. 强行使用 PIM 反而会降低计算效率

结论：**PIM 只适用于 memory-bound 程序**。它在根本上是为"数据搬运瓶颈"设计的解决方案，而非通用计算加速器。

---

## 参考文献

1. Williams, S., Waterman, A., & Patterson, D. (2009). "Roofline: An Insightful Visual Performance Model for Floating-Point Programs." *Communications of the ACM*, 52(4).
2. Putnam, A., et al. (2014). "A Reconfigurable Fabric for Accelerating Large-Scale Datacenter Services." *ISCA 2014*.
3. Nurvitadhi, E., et al. (2017). "Can FPGAs Beat GPUs in Accelerating Next-Generation Deep Neural Networks?" *FPGA 2017*.
4. Cerebras Systems. (2021). "Wafer-Scale Engine: The Largest Chip Ever Built." *Whitepaper*.
5. Kwon, Y., et al. (2021). "A 20nm 6GB HBM-PIM with Programmable ALUs." *ISCA 2021*.
6. Mutlu, O. (2021). "Processing-in-Memory: A Workload-Driven Perspective." *IBM Research*.
