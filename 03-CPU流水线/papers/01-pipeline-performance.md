# 论文笔记：CPU 流水线性能

## 论文信息

- **教材：** Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann, 2017. Chapter 4: The Processor.
- **章节重点：** Sections 4.5--4.9（流水线冒险、转发、分支预测、性能分析）

## 其他参考文献

- **Textbook:** Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann, 2019. Appendix C: Pipelining: Basic and Intermediate Concepts (and Chapter 3 for ILP).
- **Paper:** Patterson, D. A., & Sequin, C. H. "RISC I: A Reduced Instruction Set VLSI Computer." *Proceedings of the 8th Annual International Symposium on Computer Architecture (ISCA)*, 1981, pp. 443--457.
- **Paper:** Smith, J. E. "A Study of Branch Prediction Strategies." *Proceedings of the 8th Annual International Symposium on Computer Architecture (ISCA)*, 1981, pp. 135--148.

## 贡献（一句话）

Patterson 和 Hennessy 在 *Computer Organization and Design* 中对流水线的系统性论述，确立了 5 级 RISC 流水线作为经典教学模型的地位，展示了转发、冒险检测与分支预测如何共同实现接近理想的 CPI（Cycles Per Instruction，每指令周期数），并量化了理想流水线与真实流水线之间的性能差距。

## 背景：流水线为何重要

在采用流水线（pipelining）之前，CPU 采用单周期（single-cycle）或多周期（multi-cycle）实现：

| 实现方式 | 每条指令周期数 | 时钟周期 | 局限性 |
|----------------|----------------------|--------------|------------|
| 单周期   | 1                    | 最长路径（最慢指令） | 所有指令都要等待最慢的指令 |
| 多周期    | 可变（3--5）      | 均衡、更短 | 吞吐率低：同一时刻只有一个阶段处于活动状态 |
| **流水线**  | ~1（理想）           | 均衡（受阶段限制） | 冒险（hazard）会降低吞吐率 |

流水线的工作方式是将指令执行拆分为相互独立的阶段。当一条指令处于 ALU 阶段时，另一条指令正在取指，还有一条正在访问存储器，依此类推。这种**重叠（overlap）**是性能提升的根本来源。

关键洞见在于：流水线并不会降低单条指令的**延迟（latency）**（由于流水线寄存器的存在，延迟实际上会略有增加），但它能显著提高**吞吐率（throughput）**（每周期完成的指令数）。

## 关键概念

### 5 级 RISC 流水线

经典的 5 级流水线将执行过程划分为：

| 阶段 | 名称 | 发生的事情 |
|-------|------|-------------|
| IF    | 取指（Instruction Fetch） | 从指令存储器读取指令；更新 PC |
| ID    | 译码（Instruction Decode） | 读取寄存器堆；译码指令；生成控制信号 |
| EX    | 执行（Execute） | ALU 运算；有效地址计算；分支条件判断 |
| MEM   | 访存（Memory Access） | 加载/存储数据存储器访问 |
| WB    | 写回（Write Back） | 将结果写入寄存器堆 |

每个阶段之间都有一个**流水线寄存器（pipeline register）**（IF/ID、ID/EX、EX/MEM、MEM/WB），用于保存中间状态。流水线寄存器是受时钟驱动的寄存器——它们在一个周期结束时捕获数据，并在下一个周期开始时将数据呈现给下一阶段。

流水线寄存器的格式随着指令推进而扩展：

```
IF/ID:   PC + 4, instruction word
ID/EX:   PC + 4, read data 1, read data 2, immediate, rs1, rs2, rd, control signals
EX/MEM:  PC + 4, ALU result, write data, rd, control signals (narrowing)
MEM/WB:  ALU result (or memory read data), rd, control signals (narrowing)
```

### 结构冒险（Structural Hazards）

当两条指令在同一时刻需要同一硬件资源时，就会发生结构冒险。在采用独立指令存储器和数据存储器的经典 5 级流水线（哈佛架构）中，存储器访问不会产生结构冒险。然而，统一缓存（使用单一存储器端口的冯·诺依曼架构）会在 MEM 阶段的加载/存储访问与 IF 阶段的取指同时需要同一存储器时产生结构冒险。

**解决方法：** 让流水线停顿一个周期，或复制该资源（分离 I-cache 和 D-cache）。

### 数据冒险（Data Hazards）

当一条指令依赖于前一条尚未完成的指令的结果时，就会发生数据冒险。经典的三类冒险如下：

| 冒险 | 含义 | 示例 |
|--------|---------|---------|
| RAW（Read After Write，写后读） | 指令在前一条指令写入寄存器之前读取该寄存器 | `add x1,x2,x3` / `sub x4,x1,x5` |
| WAR（Write After Read，读后写） | 指令在前一条指令读取寄存器之前写入该寄存器 | 在顺序流水线中不可能发生 |
| WAW（Write After Write，写后写） | 指令在前一条指令写入寄存器之前写入该寄存器 | `add x1,...` / `sub x1,...` —— 在简单的顺序 5 级流水线中不是冒险；它在乱序/超标量设计中才会产生影响 |

**RAW 冒险**在 RISC 流水线中占主导地位。关键洞见是：ALU 指令的结果在 EX 阶段结束时即可获得（而不是在 WB 阶段），而依赖指令需要在 EX 阶段开始时使用该结果。转发/旁路会直接路由这个值。

### 转发/旁路（Forwarding/Bypassing）

转发/旁路是一种硬件技术，它在结果真正写入寄存器堆之前，将流水线阶段产生的结果直接路由回 ALU 输入端。

转发路径：

| 来源阶段 | 目标阶段 | 延迟 | 用途 |
|-------------|-------------------|---------|----------|
| EX/MEM（ALU 结果） | EX 输入 | 0 个周期（同一周期） | EX 到 EX 转发 |
| MEM/WB（ALU 结果或加载结果） | EX 输入 | 1 个周期 | MEM 到 EX 转发 |

**转发单元逻辑：** 转发单元将 EX/MEM 和 MEM/WB 中指令的目标寄存器与 EX 中指令的源寄存器进行比较。如果找到匹配项，且该指令会写入寄存器，则转发得到的值将取代从寄存器堆读出的值。

```
// Simplified forwarding logic
if (EX/MEM.RegWrite and EX/MEM.rd != 0 and EX/MEM.rd == ID/EX.rs1)
    ForwardA = 2'b10  // forward from EX/MEM
if (MEM/WB.RegWrite and MEM/WB.rd != 0 and MEM/WB.rd == ID/EX.rs1 and
    not (EX/MEM.RegWrite and EX/MEM.rd != 0 and EX/MEM.rd == ID/EX.rs1))
    ForwardA = 2'b01  // forward from MEM/WB
```

### 加载-使用冒险问题

转发无法完全解决**加载-使用冒险（load-use hazard）**，因为加载指令的数据只有在 MEM 阶段结束时才可用，而依赖指令在 EX 阶段开始时就需要该数据。结果晚到了一个周期。

```
Cycle:      1       2       3       4       5       6
lw x1,0(x2): IF      ID      EX      MEM     WB
add x3,x1,x4:         IF      ID      ID      EX     MEM ...
                              (stall)  (data ready at end of MEM)
                                      ^-- 1-cycle bubble in EX
```

加载-使用冒险所需的最小停顿是 **1 个周期**（流水线中的一个“气泡”）。硬件通过以下方式插入停顿：
1. 冻结 PC（阻止 IF 取下一条指令）
2. 冻结 IF/ID，使依赖指令停留在 ID 阶段
3. 向 ID/EX 中插入一个气泡（将控制信号置为 0），同时让加载指令继续推进到 MEM 阶段

### 控制冒险与分支预测（Control Hazards and Branch Prediction）

控制冒险源于分支和跳转指令。在计算出分支结果之前（对于简单流水线，通常在 EX 阶段），流水线无法确定下一个 PC。

分支代价取决于预测策略：

| 策略 | 描述 | 代价（跳转） | 代价（不跳转） |
|----------|-------------|-----------------|---------------------|
| 预测不跳转 | 假定分支不跳转，按顺序取指 | 2 个周期（清空 IF、ID） | 0 个周期 |
| 预测跳转 | 假定分支跳转，从目标地址取指 | 0 个周期 | 2 个周期（清空 IF、ID） |

使用**分支目标缓冲（branch target buffer，BTB）**，可以通过提早（在 IF 或 ID 阶段）预测目标地址来降低跳转时的代价。

### 流水线图约定

标准的流水线图展示各阶段随周期从左到右推进：

```
         C1    C2    C3    C4    C5    C6    C7
lw:      IF    ID    EX    MEM   WB
add:          IF    ID    EX    MEM   WB
sub:                IF    ID    EX    MEM   WB
```

停顿（气泡）表示为空阶段或被显式标记：

```
         C1    C2    C3    C4    C5    C6    C7
lw:      IF    ID    EX    MEM   WB
add:          IF    ID    BUBBLE EX   MEM   WB
sub:                IF    IF    ID   ...   ...
                  (stall)
```

## 性能模型：CPI 分析

### 理想流水线 CPI

在无冒险的理想流水线中，每个周期完成一条指令：

```
CPI_ideal = 1.0
Speedup_ideal = (1 cycle/inst) * (T_single / T_pipeline)
             = 1 * (T_single / (T_single / N))   -- N stages
             = N
```

理想情况下，一条 N 级流水线相对单周期实现可提供 N 倍加速。

### 真实流水线 CPI

真实 CPI 需要考虑流水线停顿：

```
CPI_real = 1.0 + CPI_structural + CPI_data + CPI_control
```

每一项的计算方式如下：

**结构冒险的贡献：**
```
CPI_structural = Frequency(structural_hazards) * Stall_cycles
```

**数据冒险的贡献（5 级流水线中的加载-使用停顿）：**
```
CPI_data = Frequency(loads) * Fraction(load_use) * Stall_cycles
```

**控制冒险的贡献（分支误预测）：**
```
CPI_branch = Frequency(branches) * Fraction(mispredicted) * Penalty_cycles
```

### 计算示例

已知：
- 22% 的加载指令，其中 30% 的加载会导致 RAW（加载-使用）冒险，每次停顿 1 个周期
- 15% 的分支指令，其中 60% 跳转，每次代价为 2 个周期（采用预测不跳转策略）
- 5% 的结构冒险，每次停顿 1 个周期
- 基础 CPI = 1.0

计算：

```
CPI_data      = 0.22 * 0.30 * 1     = 0.066
CPI_branch    = 0.15 * 0.60 * 2     = 0.180
CPI_structural = 0.05 * 1           = 0.050
CPI_real      = 1.0 + 0.066 + 0.180 + 0.050 = 1.296
```

相对于理想流水线的性能：1 / 1.296 = 77.2% 的理想吞吐率。

### 为何分支占主导

在上面的示例中，尽管分支只占指令的 15%，却贡献了最大的代价（0.180 CPI，即总 CPI 代价的 60.8%）。这就是为什么分支预测是计算机体系结构中最活跃的研究领域之一——即使预测准确率只有很小的提升，也会对性能产生不成比例的巨大影响。

## 我的思考

### 1. 流水线是延迟隐藏的一种实践

流水线并不会让单条指令变得更快。它将一条指令的延迟隐藏在其他指令的执行背后。这是计算机体系结构中反复出现的主题：乱序执行（out-of-order execution）、预取（prefetching）、多线程（multithreading），乃至存储层次结构（memory hierarchies）都在使用延迟隐藏。5 级流水线是这一原理最简单、最清晰的例子。

### 2. 转发与停顿之间的权衡

转发很优雅，但存在物理极限。加载-使用冒险表明，即使采用完全转发，基本的流水线深度也会在产生数据和消费数据之间造成最小延迟。这就是为什么编译器调度（重排相互独立的指令以填补加载-使用空隙）与硬件转发逻辑本身同样重要。最佳性能来自软硬件协同。

### 3. 加深流水线的收益递减

5 级流水线在教学上很方便，但商用处理器已经转向深得多的流水线（高性能 x86 中为 14--20 级）。更深的流水线允许更高的时钟频率，但会增加分支代价（预测错误时需要清空更多阶段），并产生更多转发路径。对于给定的工艺和工作负载，存在一个最优的流水线深度，而找到这一深度是一项核心工程挑战。

### 4. 分支预测是最困难的问题

在真实流水线中，控制冒险造成的危害最大，原因在于：(a) 分支很频繁（占指令的 15--25%）；(b) 预测本质上并不完美；(c) 更深的流水线会放大代价。现代处理器将大量芯片面积用于复杂的分支预测器（两级自适应预测器、神经预测器、锦标赛预测器）——这证明了该问题有多么关键。

### 5. 定量方法在实践中的应用

CPI 模型是 Patterson 和 Hennessy 定量方法最具代表性的贡献。它将性能分解为可测量的组成部分，每一部分都与特定的流水线特性相关联。这使体系结构设计师能够基于数据而非直觉做出设计决策（增加更多转发？更好的分支预测？更深的流水线？）。“铁律”（Time/Program = Instructions * CPI * Clock）仍然是基本的性能方程。

---

## 参考文献

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann, 2017. Chapter 4.
2. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann, 2019. Appendix C (Pipelining) and Chapter 3 (ILP).
3. Smith, J. E. "A Study of Branch Prediction Strategies." *Proceedings of the 8th Annual International Symposium on Computer Architecture (ISCA)*, 1981, pp. 135--148.
4. Patterson, D. A., & Sequin, C. H. "RISC I: A Reduced Instruction Set VLSI Computer." *Proceedings of the 8th Annual International Symposium on Computer Architecture (ISCA)*, 1981, pp. 443--457.
5. Harris, S., & Harris, D. *Digital Design and Computer Architecture: RISC-V Edition*. Morgan Kaufmann, 2021. Chapters 6, 7.
6. Waterman, A., & Asanovic, K. (Eds.). *The RISC-V Instruction Set Manual, Volume I: Unprivileged Architecture*. Document Version 20191213.
