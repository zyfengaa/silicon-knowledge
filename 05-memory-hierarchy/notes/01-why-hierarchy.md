# 05-01 为什么需要存储层次

## 速度、容量、成本的不可能三角

计算系统对存储有三个相互矛盾的要求：

- **快**：CPU 每个时钟周期都在等待数据，如果内存和 CPU 一样快，流水线就不会停顿。
- **大**：现代应用程序（数据库、浏览器、AI 模型）需要数百 GB 乃至 TB 级的存储。
- **便宜**：如果全部用 SRAM，一台服务器可能比一辆跑车还贵。

**不可能三角**：没有任何一种存储技术能同时满足这三个要求。SRAM（静态随机存取存储器）最快但面积大、成本高；DRAM 密度高但慢一个数量级；磁盘/SSD 容量极大但延迟高出数百万倍。

解决方案是**存储层次（Memory Hierarchy）**：用多种不同速度、容量、成本的存储介质组成一个层级结构，让程序以接近最快的速度访问接近最大的容量。

| 层次 | 典型容量 | 典型延迟 | 工艺 |
|------|---------|---------|------|
| 寄存器 | ~1 KB | ~0.3 ns (1 cycle) | 触发器 (FF) |
| L1 缓存 | 32–64 KB | ~1 ns (3–5 cycles) | SRAM |
| L2 缓存 | 256–512 KB | ~4 ns (10–15 cycles) | SRAM |
| L3 缓存 | 8–64 MB | ~10 ns (30–50 cycles) | SRAM |
| DRAM | 16–512 GB | ~100 ns (300–500 cycles) | DRAM |
| SSD (NVMe) | 256 GB–4 TB | ~1e5 ns (数十万 cycles) | NAND Flash |
| HDD | 1–20 TB | ~1e7 ns (数千万 cycles) | 磁介质 |

## 典型延迟数值表

以下数值来自 Google 工程师 Jeff Dean 的经典演讲，适合在心里时刻记住：

```
操作                    延迟（近似）       换算为时钟周期 (4 GHz)
─────────────────────────────────────────────────────────
L1 缓存引用              ~1 ns             4 cycles
L2 缓存引用              ~4 ns             16 cycles
L3 缓存引用              ~10 ns            40 cycles
主存引用 (DRAM)          ~100 ns           400 cycles
SSD 随机读               ~1e5 ns           400,000 cycles
HDD 随机读               ~1e7 ns           40,000,000 cycles
顺序从 HDD 读 1 MB       ~30,000,000 ns    120,000,000 cycles
数据包从 US 到 EU 往返   ~150,000,000 ns   600,000,000 cycles
```

这些数字说明了一个关键事实：一次主存访问的延时足够 CPU 执行 **400 条指令**。如果每次 `ld` 指令都要等内存，CPU 的利用率会低到无法接受。

## 程序访问的局部性

存储层次之所以有效，是因为程序访问内存时表现出两种局部性：

### 时间局部性（Temporal Locality）

> 刚刚访问过的数据很可能在不久后再次被访问。

- 循环体中的变量
- 频繁调用的函数代码
- 累加器（`sum += a[i]` 中的 `sum`）

### 空间局部性（Spatial Locality）

> 刚刚访问过的数据附近的数据很可能很快被访问。

- 数组顺序遍历（`a[0], a[1], a[2], ...`）
- 结构体连续访问（`p.x, p.y, p.z`）
- 取指顺序执行

从存储层次的角度，每层都会利用这两种局部性向上一层提供数据——缓存在一次未命中时会加载**整个缓存块**（利用空间局部性），并将刚访问过的数据保留在缓存中（利用时间局部性）。

## AMAT 公式

平均内存访问时间（Average Memory Access Time, AMAT）是衡量存储层次效果的定量指标：

```
AMAT = HitTime + MissRate × MissPenalty
```

- **HitTime**：在缓存中命中时读取一次数据的时间
- **MissRate**：未命中比例（缺失次数 ÷ 总访问次数）
- **MissPenalty**：未命中后从下一级存储取回数据的额外时间

**示例计算**：

```
L1: HitTime = 1 ns, MissRate = 5%, MissPenalty = 10 ns
AMAT = 1 + 0.05 × 10 = 1.5 ns
```

如果没有 L1 缓存，每次访问都要直接读 DRAM（~100 ns），慢 66 倍。

对于多级缓存（L1 → L2 → L3 → DRAM），AMAT 可以递归计算：

```
AMAT_L1 = HitTime_L1 + MissRate_L1 × (HitTime_L2 + MissRate_L2 × (HitTime_L3 + MissRate_L3 × MissPenalty_DRAM))
```

## 关键概念

- **存储层次**：用多级不同速度/容量的存储介质弥合 CPU 与主存的速度差距
- **局部性**：时间局部性和空间局部性是层次结构生效的物理基础
- **AMAT**：量化多层次结构的平均访问延迟
- **不可能三角**：没有任何单一技术同时满足快、大、便宜

## 参考文献

- Hennessy, J. L. & Patterson, D. A., *Computer Architecture: A Quantitative Approach*, 6th ed., Chapter 2: Memory Hierarchy Design.
- Dean, J., "Software Engineering Advice from Building Large-Scale Distributed Systems", Google, 2009. — "Latency Numbers Every Programmer Should Know".
- Patterson, D. A. & Hennessy, J. L., *Computer Organization and Design: The Hardware/Software Interface*, Chapter 5: Large and Fast: Exploiting Memory Hierarchy.
- Drepper, U., "What Every Programmer Should Know About Memory", Red Hat, 2007. Section 2: CPU Caches.
