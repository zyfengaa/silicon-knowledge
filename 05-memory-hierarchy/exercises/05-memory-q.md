# 模块 05：存储器层次结构（Memory Hierarchy）-- 练习题

## 05-memory-q.md：问题与练习

---

## 第 1 节：Tag / Index / Offset 计算（Tag / Index / Offset Calculation）

### 问题 1

计算地址 `0xABCD1234` 在两种不同缓存配置中的 tag、index 和 offset 位，两种配置的缓存行大小均为 64 B。

a) **直接映射缓存（Direct-mapped cache），总大小 32 KB。** 展示位划分（哪些位构成 offset，哪些构成 index，哪些构成 tag）。从地址中提取实际的字段值。

b) **4 路组相联缓存（4-way set-associative cache），总大小 32 KB。** 再次展示位划分和提取的字段值。

c) 每种配置有多少个组（sets）？相联度（associativity）如何改变 index 字段的宽度（与直接映射情况相比）？

### 问题 2

将以下访问序列中的每次缺失分类为**强制性缺失/冷缺失（compulsory / cold miss）**、**冲突缺失（conflict miss）**或**容量缺失（capacity miss）**。假设：

- 缓存：4 组，1 路（直接映射），每行 2 个字（每行 8 字节）
- 地址以**字地址（word addresses）**给出（每个地址指向一个 4 字节的字）
- 缓存初始为空（cold）

访问序列（字地址）：`0, 8, 0, 16, 8, 0, 24, 32, 0, 8`

对于每次访问，确定：

a) 它映射到的组
b) 是命中（hit）还是缺失（miss）
c) 缺失类型（compulsory, conflict, 或 capacity）
d) 解释每种分类的理由

---

## 第 2 节：AMAT 与多级缓存（AMAT and Multi-Level Caches）

### 问题 3

一个系统具有以下存储器层次结构参数：

| 层级 | 命中时间（Hit Time） | 缺失率（局部 Miss Rate） |
|-------|----------|-------------------|
| L1 | 1 周期 | 5% |
| L2 | 10 周期 | 20% |
| 主存（Main memory） | 100 周期 | --（假设 100% 缺失惩罚） |

a) 计算完整层次结构（L1 + L2 + 主存）的 **AMAT**。展示计算过程。

b) 计算去掉 L2 后的 **AMAT**（即只有 L1 + 主存，L1 缺失直接以 100 周期访问主存）。

c) 比较两个 AMAT 值。L2 缓存将平均访问时间提高了多少倍？

d) 如果我们可以选择在 L2 和主存之间添加一个 L3 缓存（命中时间 = 30 周期，局部缺失率 = 25%）而不是仅依赖 L2，计算新的 AMAT。考虑到成本和复杂度，L3 是否值得添加？

---

## 第 3 节：写入策略（Write Policies）

### 问题 4

比较**写直达（write-through）**和**写回（write-back）**策略在以下访问模式下的表现：

一个程序对一个**32 字节块**内的地址进行顺序写入，重复 4 次：

```
Write addr 0x00, Write addr 0x04, Write addr 0x08, ..., Write addr 0x1C
（每次迭代 8 次写入，4 次迭代 = 共 32 次写入）
```

假设：

- 缓存行大小 = 32 字节（一行容纳整个块）
- 缓存初始为空（cold）
- **写直达**：每次写入立即进入内存；不写分配（write-allocate，写入缺失时直接写入内存，不将行加载到缓存中）
- **写回**：写分配（缺失时加载行），仅被逐出的脏行才写回内存
- 没有其他访问干扰（在写回策略下，该块停留在缓存中）

a) 对于**写直达**，计算内存写入的总次数（包括由缺失导致的缓存行填充引起的写入，如果有的话）。其中有多少次写入是针对该 32 字节块的，多少次是其他位置的？

b) 对于**写回**，计算内存写入的总次数（包括逐出时的写回和缺失时的行填充）。

c) 假设写直达策略使用一个**写缓冲区（write buffer）**来批量处理写入。与写回相比，这对性能有何影响？在什么条件下写直达仍然更受青睐？

---

## 第 4 节：TLB 覆盖范围（TLB Reach）

### 问题 5

考虑一个全相联（fully associative）的 TLB（Translation Lookaside Buffer），有 **64 个条目**。

a) **4 KB 页面的 TLB 覆盖范围**：TLB 在不触发页表遍历（page walk）的情况下可以覆盖多大的虚拟地址范围（以字节为单位）？

b) **2 MB 页面的 TLB 覆盖范围**：使用相同的 64 个条目，覆盖范围是多少？

c) 使用 4 KB 页面覆盖 **512 GB** 的虚拟地址空间需要多少个 TLB 条目？

d) 一个现代数据库服务器的工作集大约为 200 GB。讨论 TLB 覆盖范围对此工作负载的实际影响。2 MB 页面（或 1 GB 页面）会如何改变情况？

e) 一些较新的处理器（例如 Intel Ice Lake, AMD Zen 3+）包含一个**二级 TLB（L2 TLB）**，拥有数千个条目。解释这为什么有帮助，以及它代表了什么样的设计权衡（trade-off）。

---

## 第 5 节：应用题（Applied Problems）

你可以用自由文本或计算值回答，适用时展示推理过程。

---

## 参考公式（Reference Formulas）

- 缓存容量 = 组数 x 相联度 x 行大小
- Index 位数 = log2(组数)
- Offset 位数 = log2(行大小)
- Tag 位数 = 地址宽度 - index 位数 - offset 位数
- AMAT = 命中时间 + 缺失率 x 缺失惩罚
- TLB 覆盖范围 = 条目数 x 页面大小

---

## 答题指南（Answer Guidelines）

- 对于问题 1，将地址用二进制表示，并画线分隔 tag、index 和 offset 字段。然后计算数值。
- 对于问题 2，考虑每次缺失是否在全相联缓存中仍然会发生（容量缺失），或是由于与另一个地址冲突引起的（冲突缺失），或者是首次访问（强制性缺失）。
- 对于问题 3-5，展示所有公式和中间步骤。

---

## 参考文献（References）

1. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 第 6 版. Morgan Kaufmann, 2019. 第 2 章（Memory Hierarchy Design）。
2. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann, 2017. 第 5 章（Large and Fast -- Exploiting Memory Hierarchy）。
3. Hill, M. D., & Smith, A. J. "Evaluating Associativity in CPU Caches." *IEEE Transactions on Computers*, Vol. 38 No. 12, 1989.
4. Intel Corporation. *Intel 64 and IA-32 Architectures Optimization Reference Manual*. 关于 TLB 组织和页面大小的章节。
