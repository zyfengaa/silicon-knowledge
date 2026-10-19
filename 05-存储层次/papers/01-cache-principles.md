# 论文笔记：缓存设计原理

## 论文信息

本笔记综合了以下来源中对缓存存储器（cache memory）的论述：

- **教材：** Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann, 2019. Chapter 2: Memory Hierarchy Design.
- **教材：** Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann, 2017. Chapter 5: Large and Fast -- Exploiting Memory Hierarchy.

## 一句话贡献

缓存利用时间局部性（temporal locality）和空间局部性（spatial locality），弥合快速处理器与缓慢主存之间不断扩大的延迟差距；其有效性由一小组设计参数——容量、相联度（associativity）、缓存行大小、替换策略（replacement policy）和写策略（write policy）——决定，这些参数构成了一组已被充分理解的权衡。

## 背景：为什么需要缓存

历史上，处理器时钟频率大约每年提升 50%，而 DRAM 访问延迟每年仅改善约 7%。这一不断扩大的差距被称为**内存墙（memory wall）**，意味着一次主存访问可能耗费数百个处理器周期。现代乱序核心（out-of-order core）在解决一次缓存未命中所需的时间内，可能发射数十到数百条指令。

缓存位于 CPU 与主存之间，存储最近使用的数据和指令，使未来的访问能够由快速的片上存储来服务。关键的洞见是**局部性（locality）**：

- **时间局部性（Temporal locality）**：若某个位置被访问，它很可能很快被再次访问（例如循环计数器、栈帧）。
- **空间局部性（Spatial locality）**：若某个位置被访问，附近的位置很可能很快被访问（例如数组遍历、顺序取指）。

## 关键概念

### 1. 直接映射缓存（Direct-Mapped Cache）

最简单的组织方式：每个内存地址恰好映射到一条缓存行（cache line）。地址被划分为标记（tag）、索引（index）和偏移（offset）。索引选择一行；标记用于比对，以验证该行保存的正是所需的数据块。

**优点**：简单、快速（只需一个比较器）、功耗低。**缺点**：冲突未命中率高——若两个频繁访问的地址映射到同一行，它们会反复相互驱逐（抖动，thrashing）。

### 2. 组相联缓存（Set-Associative Cache）

每个组（set）包含 N 路（way，即行）。一个内存地址恰好映射到一个组，但可以占据该组内 N 行中的任意一行。与直接映射相比，N 路组相联缓存减少了冲突未命中，代价是额外的比较器和略高的访问延迟。

- 1 路 = 直接映射
- N 路，其中 N = 总行数 = 全相联

真实缓存通常是 2 到 16 路组相联。L1 缓存倾向于较低的相联度（更快），而最后一级缓存（last-level cache，LLC）倾向于较高的相联度（更高的命中率）。

### 3. 替换策略（Replacement Policy）

当发生未命中且组已满时，必须驱逐一行。常见策略：

- **LRU（Least Recently Used，最近最少使用）**：替换最久未被访问的行。在许多工作负载上表现良好，但理论上并非最优（需要未来知识的 Belady OPT/MIN 才是最优），而且在高相联度下实现代价高昂（每次访问都需要更新状态）。
- **伪 LRU（Pseudo-LRU，Tree-PLRU）**：用一棵由位构成的二叉树来近似 LRU。用于一些真实处理器；厂商通常不公开确切的替换策略，而且它可能因微架构而异。
- **随机/NRU（Random/NR U）**：简单但可预测性较差。用于一些高相联度、精确 LRU 代价过高的缓存。

### 4. 写策略（Write Policy）

处理写操作有两种主要策略：

- **写直达（Write-Through）**：每次写都会同时更新缓存和内存。简单，并确保内存始终保有最新值，但会产生大量内存流量。通常与**写缓冲（write buffer）**配合使用，以避免每次写都让 CPU 停顿。

- **写回（Write-Back）**：写操作只更新缓存行；该行被标记为**脏（dirty）**。当该行被驱逐时，其内容被写回内存。对于重复写同一位置更高效，但更复杂（多核需要一致性协议）。

每种写策略都伴随一个**写分配（write-allocate）**（写未命中时将该行取入缓存）或**非写分配（no-write-allocate）**（不缓存而直接写入内存）的子策略。

## 缓存未命中的三类（The Three C's）

Hill 和 Smith（1989）将未命中分为三类，即广为人知的**三类 C（Three C's）**：

| 类别                  | 成因                                              | 可通过以下方式减少                     |
|----------------------|---------------------------------------------------|----------------------------------------|
| 强制性（Compulsory）   | 对数据块的首次访问——此时缓存为空                    | 更大的块大小（空间局部性）；预取          |
| 容量（Capacity）       | 工作集超过缓存容量；数据块被驱逐后又重新取回          | 更大的缓存                             |
| 冲突（Conflict）       | 多个块映射到同一个组，相互驱逐                      | 更高的相联度；更好的放置函数             |

第四个“C”——**一致性（Coherence）**——有时会被加入多处理器系统，其中缓存行会因其他核心的写操作而失效。

### 实践观察

- 在调优良好的应用中，强制性未命中通常只占总未命中的一小部分。
- 对于大工作集，容量未命中占主导，可通过增大缓存容量来解决。
- 冲突未命中对缓存组织方式最敏感——对于规则的访问模式，将相联度翻倍通常能消除大部分冲突未命中。
- 未命中率与缓存容量之间的关系遵循幂律：缓存容量翻倍通常会使未命中率降低约 30–50%，不过这因工作负载而异。

## 性能影响

### 平均内存访问时间（Average Memory Access Time，AMAT）

基本性能模型为：

```
AMAT = Hit Time + Miss Rate * Miss Penalty
```

对于多级层次结构：

```
AMAT = L1_HitTime
       + L1_MissRate * (L2_HitTime
                        + L2_MissRate * (L3_HitTime
                                         + L3_MissRate * MemPenalty))
```

**关键洞见**：降低未命中率是有价值的，但未命中率与未命中代价的乘积意味着，如果未命中代价很大（例如 DRAM 的 100 多个周期），即使很小的未命中率也可能代价高昂。

### 未命中代价之墙

随着处理器变得更快，以损失指令数衡量的未命中代价不断增大。一个 4 GHz、4 宽发射（4-wide issue）的核心在一次 L3 未命中上可能损失 400 多条指令的潜在工作。这推动了：

- 更大的 L2/L3 缓存（可达数十 MB）
- 硬件预取器（hardware prefetcher），在被需要之前预测并取入数据块
- 乱序执行（out-of-order execution），将未命中延迟与其他工作重叠
- 同时多线程（Simultaneous Multithreading，SMT），在未命中期间切换到另一个线程

### 带宽与延迟

现代优化越来越关注带宽（每周期可移动多少字节），其程度与关注延迟相当。设计良好的缓存层次结构提供：

- 对频繁访问提供**低延迟**（L1：1–4 个周期）
- 对批量数据移动提供**高带宽**（L2/L3：每周期数十字节）
- 对超过 L1 的工作集提供**大容量**（LLC：MB 级）

## 我的思考

1. **缓存无关与缓存感知编程（Cache-oblivious vs cache-aware programming）**：教材中描述的平铺（分块，tiling/blocking）优化是缓存感知的（cache-aware）——程序员根据已知的缓存参数选择平铺大小。缓存无关算法（cache-oblivious algorithm，例如递归分治）在不知道缓存大小的情况下也能获得良好的缓存行为，但通常开销更高。这两种方法都是体系结构如何影响算法设计的迷人例子。

2. **相联度并非免费**：虽然更高的相联度会减少冲突未命中，但它会增加访问延迟（更多标记比较）和功耗。在实践中，L1 缓存通常采用 2–8 路，并通过精心布局来尽量减小对延迟的影响；而 LLC 采用 16 路或更多，因为在那里延迟相对不那么重要。这是 Patterson 和 Hennessy 所倡导的定量方法的一个具体例子：先测量，再设计。

3. **机器学习驱动预取的兴起**：近期研究（例如 2022–2025 年 ISCA/MICRO 会议论文集上的工作）探索使用神经网络进行缓存预取和替换。虽然教材中的 LRU 仍是所教授的基础，但许多真实处理器现在使用厂商特定的自适应替换策略；确切的算法通常不公开，因此关于某个特定产品使用了某个具名算法的说法应谨慎对待。

4. **TLB 作为一种特殊缓存**：转换后备缓冲器（Translation Lookaside Buffer，TLB）在概念上只是另一种缓存，但其性能影响是全有或全无的——一次 TLB 未命中可能耗费数百到数千个周期，因为它可能需要在内存中遍历多级页表。现代操作系统转向更大的页面大小（2 MB、1 GB），直接原因就是 TLB 覆盖范围（TLB reach）方面的担忧，对于数据库和 AI 推理服务器等大内存应用尤其如此。

---

## 参考文献

1. Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*. 6th Edition. Morgan Kaufmann, 2019. Chapter 2 (Memory Hierarchy Design). -- Core coverage of cache fundamentals, AMAT, and the Three C's.
2. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann, 2017. Chapter 5 (Large and Fast -- Exploiting Memory Hierarchy). -- Accessible introduction to cache organisation.
3. Hill, M. D., & Smith, A. J. "Evaluating Associativity in CPU Caches." *IEEE Transactions on Computers*, Vol. 38 No. 12, 1989, pp. 1612--1630. -- The paper that introduced the Three C's miss classification.
4. Smith, A. J. "Cache Memories." *ACM Computing Surveys*, Vol. 14 No. 3, 1982, pp. 473--530. -- Classic survey of early cache design.
5. Drepper, U. "What Every Programmer Should Know About Memory." Red Hat, 2007. -- Practical programmer-oriented guide to the memory hierarchy.
6. Jacob, B., Ng, S. W., & Wang, D. T. *Memory Systems: Cache, DRAM, Disk*. Morgan Kaufmann, 2007. -- Comprehensive reference on memory-system design.
7. Intel Corporation. *Intel 64 and IA-32 Architectures Optimization Reference Manual*. -- Hardware-specific cache organisation and tuning guidance.
