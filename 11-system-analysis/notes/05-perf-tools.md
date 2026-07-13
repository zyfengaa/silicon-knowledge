# Linux perf 工具：CPU 性能分析基础

## 为什么讲这个

在系统性能工程中，CPU 是最核心的计算资源。理解 CPU 上程序的运行行为——指令执行了多少、缓存命中率如何、分支预测是否准确——是性能优化的第一步。Linux `perf` 工具（Performance Counters for Linux）是 Linux 内核自带的性能分析框架，它利用 CPU 内置的性能监控单元（PMU, Performance Monitoring Unit）来收集硬件事件数据，几乎零开销地提供底层性能洞察。无论你是调试一个慢速程序、分析系统瓶颈还是做微架构级别的优化，`perf` 都是必备工具。

## 核心概念

### 性能计数器（Performance Counter）

现代 CPU 内部集成了数十到数百个**性能监控计数器（PMC, Performance Monitoring Counter）**，每个计数器可以配置为统计某种硬件事件。常见的事件包括：

| 事件类别 | 典型事件 | 含义 |
|---------|---------|------|
| 指令 | `instructions` | 执行的指令数（retired） |
| 周期 | `cycles` | CPU 时钟周期数 |
| 缓存 | `cache-misses`, `cache-references` | 最后一级缓存（LLC）未命中次数 |
| 分支 | `branch-misses`, `branch-instructions` | 分支预测失败次数 |
| TLB | `dTLB-load-misses`, `iTLB-load-misses` | TLB 未命中次数 |
| 内存 | `mem-loads`, `mem-stores` | 内存加载/存储操作次数 |

这些事件通过 CPU 的 MSR（Model-Specific Register）进行编程和读取。perf 利用内核的 perf_event_open 系统调用来配置和访问这些寄存器。

### IPC：每周期指令数

IPC（Instructions Per Cycle，每周期指令数）是衡量 CPU 执行效率的核心指标：

$$
\text{IPC} = \frac{\text{指令数}}{\text{时钟周期数}}
$$

- IPC > 1：每个周期执行多条指令（理想情况）
- IPC ≈ 1：每个周期执行一条指令
- IPC < 1：存在执行停顿（缓存未命中、分支预测错误、数据依赖等）

高 IPC 不一定意味着高性能——例如一个死循环的 IPC 可能很高但不做有用工作。IPC 需要结合具体上下文解读。作为参考，SPEC CPU 基准测试的 IPC 通常在 0.5-3.0 之间，取决于程序和微架构。

## perf stat：事件计数

`perf stat` 是最基本的 perf 子命令，它运行一个程序并在结束后输出汇总的事件计数。

### 基本用法

```bash
# 统计程序运行期间的硬件事件
perf stat ./my_program

# 统计特定事件
perf stat -e cycles,instructions,cache-misses,cache-references ./my_program

# 统计所有硬件事件
perf stat -e task-clock,cycles,instructions,cache-references,cache-misses,branches,branch-misses ./my_program

# 多运行取平均
perf stat -r 5 ./my_program
```

### 输出解读示例

```bash
$ perf stat ./matmul_1024

 Performance counter stats for './matmul_1024':

         12,345.67  msec task-clock                #    1.000 CPUs utilized
     45,678,901,234  cycles                        #    3.700 GHz
     67,890,123,456  instructions                  #    1.49  insn per cycle
      1,234,567,890  cache-references              #  100.000 M/sec
        123,456,789  cache-misses                  #   10.00% of all cache refs
      5,678,901,234  branches                      #  459.923 M/sec
         56,789,012  branch-misses                 #    1.00% of all branches

      12.345678901 seconds time elapsed
```

关键解读点：

1. **IPC = 1.49**：每个周期执行约 1.49 条指令。对于矩阵乘法，现代 CPU 在优化良好的情况下 IPC 可达 2-3，1.49 说明存在一定程度的等待。
2. **缓存未命中率 = 10%**：10% 的 L3 cache 访问未命中，意味着相当一部分数据需要从主存加载。对于 1024×1024 的矩阵乘法，如果没有分块优化，缓存未命中率会更高。
3. **分支误预测率 = 1.0%**：1% 的分支预测失败率对矩阵乘法来说偏高——矩阵乘法的内层循环是规律性很强的循环，分支预测应该几乎 100% 准确。偏高的误预测率可能意味着编译器生成了边界检查代码。

### 识别典型瓶颈

**高缓存未命中率（> 20%）**：
- 程序的数据集太大，无法放入缓存
- 数据访问模式是步长大的（stride）或随机的（pointer chasing）
- 优化方向：循环分块（tiling）、数据布局优化（SoA vs AoS）、预取（prefetching）

**低 IPC（< 1.0）**：
- 有频繁的缓存未命中导致流水线停顿
- 存在长延迟指令（如除法、sqrt）
- 存在频繁的分支预测错误
- 优化方向：减少数据依赖、提高指令级并行、向量化

**高分文误预测率（> 5%）**：
- 循环中存在难以预测的条件分支
- 优化方向：分支消除（使用谓词指令）、避免数据驱动的分支模式

## perf record / report：采样分析

当需要找到程序中的热点（hot spot）时，使用 `perf record` 进行采样分析。

### 基本用法

```bash
# 以 99 Hz 的频率对 CPU 周期采样
perf record -F 99 ./my_program

# 对特定事件采样（如缓存未命中）
perf record -e cache-misses -F 99 ./my_program

# 生成调用链
perf record -F 99 --call-graph dwarf ./my_program

# 查看采样报告
perf report

# 交互式导航
perf report --hierarchy
```

### 工作原理

perf record 使用 CPU 的**性能中断**机制：当配置为周期采样的计数器溢出时，CPU 触发一个中断，perf 在内核中断处理程序中记录当前程序计数器（PC）的值和调用栈。采样频率通常设为 50-1000 Hz，频率过高会增加采样开销。

采样的依据是**统计推理**：如果一个函数在采样结果中出现 x% 的次数，那么它消耗的 CPU 时间大约为 x%。这种方法的优点是开销极低（通常 < 5%），适合分析长时间运行的复杂程序。

### 输出解读

```bash
$ perf report

  Samples: 47K of event 'cycles'
  Event count (approx.): 12345678901

  Children    Self    Command     Shared Object     Symbol
  +   95.2%   0.0%    matmul      matmul            [.] main
  +   95.2%   2.3%    matmul      matmul            [.] matmul_kernel
  +   90.1%  85.3%    matmul      matmul            [.] dgemm_kernel_main
  +    5.0%   4.8%    matmul      libc-2.31.so      [.] __memcpy_avx_unaligned
```

解读要点：
- **Self** 列：函数自身消耗的 CPU 时间比例（不包含其调用的子函数）
- **Children** 列：函数及所有子函数消耗的 CPU 时间比例
- `dgemm_kernel_main` 占 85.3% 的 Self 时间，说明这就是热点函数
- 如果 `__memcpy_avx_unaligned` 出现在热点中，可能有大量数据拷贝

## perf annotate：源码级热点

在找到热点函数后，用 `perf annotate` 查看源码级的详细分析：

```bash
# 生成带源码注释的分析
perf annotate --stdio

# 查看特定函数
perf annotate --stdio dgemm_kernel_main
```

输出示例（简化）：

```
       │    for (i = 0; i < N; i++) {
  5.32 │      add      rsp, 0x8
       │        for (j = 0; j < N; j++) {
  0.12 │        mov     eax, DWORD PTR [rdi]
       │          for (k = 0; k < N; k++) {
 12.45 │  1a30:  vmovsd  xmm0, QWORD PTR [rsi+rcx*8]
 15.23 │  1a35:  vfmadd231sd xmm0, xmm1, QWORD PTR [rdx+rax*8]
 10.12 │  1a3a:  add     rcx, 0x1
  1.23 │  1a3e:  cmp     rcx, 0x400
  0.05 │  1a45:  jl      1a30
```

左边百分比表示每条指令消耗的 CPU 时间比例。从中可以看出：
- `vfmadd231sd`（融合乘加）占了 15.23% 的周期——这是核心计算指令
- 循环的地址计算开销（add、mov）加起来也不小
- 如果 `vmovsd`（加载数据）占的比例异常高，意味着 L1 cache 未命中频繁

## Flame Graph：火焰图

火焰图由 Brendan Gregg 发明，是可视化 perf 采样数据的最佳方式。

### 生成方法

```bash
# 1. 采集调用栈数据
perf record -F 99 --call-graph dwarf ./my_program

# 2. 使用 Brendan Gregg 的脚本生成火焰图
git clone https://github.com/brendangregg/FlameGraph
cd FlameGraph
perf script > out.perf
./stackcollapse-perf.pl out.perf > out.folded
./flamegraph.pl out.folded > flame.svg
```

### 解读火焰图

火焰图的 x 轴表示采样宽度（与 CPU 时间成正比），y 轴表示调用栈深度。每个矩形是一个函数调用。关键解读方法：

1. **看顶层**：最顶层是 CPU 实际执行代码的函数。宽矩形说明该函数消耗了大量 CPU 时间。
2. **看"山峰"**：如果火焰图看起来像"平顶山"（顶部很宽），说明程序的主要时间花在少数几个函数中。
3. **看颜色**（可选约定）：红色表示内核态、橙色表示用户态、黄色/绿色表示 I/O 等待等。
4. **看"烟囱"**：垂直方向高大的调用链可能暗示有深层嵌套调用的开销。

## 实际案例：矩阵乘法优化

以下是一个使用 perf 指导矩阵乘法优化的完整流程：

### 步骤 1：基线测量

```c
// naive_matmul.c
void matmul(float *A, float *B, float *C, int N) {
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++)
            for (int k = 0; k < N; k++)
                C[i * N + j] += A[i * N + k] * B[k * N + j];
}
```

```bash
gcc -O2 -o naive_matmul naive_matmul.c
perf stat ./naive_matmul 1024
```

输出特征：
- IPC ≈ 0.5-0.8（远低于 1.0）
- L1 cache-misses 非常高（因为 B 的列访问不连续）
- 缓存未命中率达到 40-60%

### 步骤 2：循环交换优化

将 j 和 k 循环交换，使 B 的访问变为行连续：

```c
void matmul_ijk(float *A, float *B, float *C, int N) {
    for (int i = 0; i < N; i++)
        for (int k = 0; k < N; k++)
            for (int j = 0; j < N; j++)
                C[i * N + j] += A[i * N + k] * B[k * N + j];
}
```

perf 观察：
- 缓存未命中大幅下降
- IPC 提升到 1.2-1.5

### 步骤 3：分块（tiling）

```c
void matmul_tiled(float *A, float *B, float *C, int N, int TILE) {
    for (int i = 0; i < N; i += TILE)
        for (int j = 0; j < N; j += TILE)
            for (int k = 0; k < N; k += TILE)
                for (int ii = i; ii < i + TILE; ii++)
                    for (int kk = k; kk < k + TILE; kk++)
                        for (int jj = j; jj < j + TILE; jj++)
                            C[ii * N + jj] += A[ii * N + kk] * B[kk * N + jj];
}
```

perf 观察：
- L2/L3 缓存未命中进一步降低
- IPC 提升到 2.0+
- 最终性能达到峰值 80-90%

## 总结

Linux perf 工具集提供了从粗粒度事件计数到细粒度采样的完整性能分析能力：
- `perf stat` 回答"程序的整体行为如何？"
- `perf record` + `perf report` 回答"程序的时间花在了哪里？"
- `perf annotate` 回答"代码行的热点在哪里？"
- 火焰图提供了直观的调用栈可视化
- 通过反复测量和优化，可以使程序从内存受限转向计算受限，最终达到接近硬件峰值

## 参考文献

1. Gregg, B. *Systems Performance: Enterprise and the Cloud*. 2nd Edition, Addison-Wesley, 2020. — 第 6-8 章详细讨论了 perf 和火焰图的使用方法
2. [Linux perf Wiki](https://perf.wiki.kernel.org/) — perf 工具的官方文档和教程
3. Gregg, B. "The Flame Graph." *Communications of the ACM*, 59(6), 2016. — 火焰图方法的原创论文，解释了可视化采样数据的设计原理
4. Intel Corporation. "Intel 64 and IA-32 Architectures Software Developer's Manual, Volume 3B: System Programming Guide, Part 2." — PMU（性能监控单元）的硬件规格和事件编程接口
5. AMD Corporation. "AMD Processor Programming Reference (PPR)." — AMD 处理器的 PMU 事件规范
6. Weaver, V. M. "Linux perf_event Features and Overhead." *The 2nd International Workshop on Performance Analysis of Workload Optimized Systems (FastPath)*, 2013. — 分析了 perf 工具的开销和限制
