# 01 — 超标量（Superscalar）

## 概述

超标量处理器是现代高性能 CPU 的核心设计思想：**每个时钟周期发射（issue）多条指令**。这与标量流水线（每个周期仅发射一条指令）形成鲜明对比。

> 标量流水线：IPC（Instructions Per Cycle）上限 = 1  
> 超标量处理器：IPC 上限 = 发射宽度（Issue Width）

## 发射宽度与多发射架构

发射宽度指处理器每周期最多能发射的指令数。常见设计：

| 处理器 | 发射宽度 | 说明 |
|--------|----------|------|
| 经典 5 段流水线 | 1 | 每周期一条指令 |
| Intel Pentium | 2 | 双发射，u/v 管道 |
| Intel Core 2 | 4 | 4-wide |
| Intel Golden Cove (P-core) | 6 | 6-wide decode |
| Apple M1 Firestorm | 8 | 8-wide decode |
| AMD Zen 4 | 8 | 8-wide front end |

**多发射的两种方式：**

1. **静态调度（VLIW）**：编译器负责将多条独立指令打包。由 Itanium（IA-64） 等架构采用，但通用性能有限。
2. **动态调度（Superscalar）**：硬件在运行时动态检测指令独立性并同时发射。几乎所有现代高性能 CPU 都采用此方法。

## 超标量的三大限制（Limits of Superscalar）

无论发射宽度多大，实际 IPC 受以下三种限制制约：

### 1. 结构冲突（Structural Hazard）

硬件资源不足，无法同时满足多条指令的需求。

例子：CPU 只有一个整数乘法器，但两条乘法指令试图同时发射 → 结构冲突。

解决方案：增加功能单元数量、采用流水线化的功能单元。

### 2. 数据相关（Data Dependence / True Data Hazard）

RAW（Read After Write）冲突。指令 B 需要指令 A 的计算结果，因此必须等待 A 完成。

```
ADD X1, X2, X3   ; 写入 X1
SUB X4, X1, X5   ; 读取 X1 → RAW 依赖，必须等待 ADD 完成
```

数据相关是**真正的限制**——它反映了计算的内在逻辑顺序，无法消除，只能通过转发（forwarding）减少等待。

### 3. 控制相关（Control Dependence / Control Hazard）

分支指令之后的指令是否执行取决于分支结果。超标量处理器必须准确预测分支方向，否则宽发射会放大浪费（一次误预测清空的多条指令数随发射宽度增加）。

```
BEQ X1, X2, label  ; 条件分支
ADD X3, X4, X5     ; 是否执行？取决于分支结果
```

## 超标量性能分析

### 理想情况 vs 实际情况

假设一个 4-wide 超标量处理器：

- **理想（CPI = 0.25）**：每周期完成 4 条指令，无任何停顿。
- **实际（CPI ~ 0.5 ~ 1.0）**：各种冲突导致部分发射槽空闲。

### 影响因素

1. **程序的指令级并行度（ILP, Instruction-Level Parallelism）**：程序本身有多少条并行可执行的指令。ILP 由数据流图决定。
2. **编译器优化**：指令重排、循环展开、软件流水线等，可以暴露更多的 ILP。
3. **硬件的调度能力**：乱序执行（Out-of-Order Execution）能进一步提高并行度。

### ILP 天花板

研究表明，即使采用无限资源（完美分支预测、无限功能单元），典型程序的 ILP 在 2 ~ 6 之间（Wall & Lim 研究）。这从根本上限制了超标量处理器的回报：

- 2-wide → 4-wide：性能提升显著
- 4-wide → 8-wide：提升有限
- 8-wide → 12-wide：边际收益极低

这就是为什么现代处理器大多为 4~8 发射，而非 16+ 发射。

## 超标量 vs 标量流水线

| 特性 | 标量流水线 | 超标量 |
|------|-----------|--------|
| 每周期发射指令数 | 1 | 多（2~8） |
| 硬件复杂度 | 低 | 高 |
| 关键路径 | 数据转发 | 指令调度 + 分支预测 |
| 功耗 | 低 | 高 |
| IPC 上限 | 1 | 发射宽度 |
| 典型应用 | 嵌入式、低功耗设备 | 高性能桌面、服务器 |

## 从超标量到乱序

超标量多发射可以看作一个"扁平化"的扩展——它只是增加了每周期发射的指令数量。但**当遇到数据相关时，超标量处理器仍然会停顿**。

那如果我们让后面不相关的指令"跳过"阻塞的指令先执行呢？这就是**乱序执行**（Out-of-Order Execution）的核心思想，将在下一节详细讲解。

## 关键概念总结

- **Issue Width（发射宽度）**：处理器每周期最多发射的指令数
- **IPC / CPI**：实际每周期完成的指令数，通常远低于发射宽度
- **ILP（指令级并行）**：程序内在的并行度，由数据流决定
- **三大限制**：结构冲突、数据相关、控制相关

## 思考题

1. 如果一个 CPU 的发射宽度是 6，但实际 IPC 只有 1.5，请分析可能的原因。
2. 为什么 8-wide 以上的超标量设计回报率越来越低？
3. 编译器如何通过循环展开来提高超标量处理器的利用率？

## 参考文献

- Hennessy, J. L. & Patterson, D. A. *Computer Architecture: A Quantitative Approach*, 6th Edition, Chapter 3: Instruction-Level Parallelism and Its Exploitation.
- Smith, J. E. & Sohi, G. S. "The Microarchitecture of Superscalar Processors." *Proceedings of the IEEE*, 1995.
- Patt, Y. N. et al. "Critical Issues Regarding HPS, A High Performance Microarchitecture." *MICRO*, 1985.
- Wall, D. W. "Limits of Instruction-Level Parallelism." *ACM ASPLOS*, 1991.
