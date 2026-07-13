# 05-02 缓存基础

## 缓存的核心概念

缓存（Cache）是一个小而快的存储器，用于保存频繁访问的数据副本。它的工作原理基于程序访问的局部性：如果软件能够有效利用局部性，缓存就能在大多数情况下提供服务，从而避免访问慢速主存。

### 缓存行 / 块

缓存与主存之间传输数据的最小单位称为**缓存行（Cache Line / Cache Block）**。现代 CPU 的缓存行大小通常为 **64 字节**（x86-64、ARMv8、RISC-V 的常见实现）。

```
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ B0  │ B1  │ B2  │ B3  │ ... │     │     │ B63 │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
└─────────────── 64 字节 ────────────────┘
```

当 CPU 访问一个字节时，硬件会将包含该字节的整个缓存行从主存读入缓存。这样，对附近字节的后续访问就能直接从缓存获取。

## 命中与缺失

| 状态 | 描述 |
|------|------|
| **Hit（命中）** | CPU 请求的数据在缓存中，可以在 HitTime 内返回 |
| **Miss（缺失）** | CPU 请求的数据不在缓存中，需要从下一级存储取回 |

一个缓存缺失的典型流程：

1. CPU 发出 `ld` 指令，地址发送到缓存控制器
2. 缓存控制器判断该地址不在缓存中 → **Miss**
3. 从下一级（L2 / L3 / DRAM）取回整条缓存行（通常需要数十到数百个周期）
4. 将该缓存行写入缓存，同时将请求的数据返回给 CPU
5. CPU 继续执行

## 缓存缺失的三种类型

### 1. 冷缺失（Cold / Compulsory Miss）

第一次访问某个数据时，缓存中必然不存在。这种缺失无法避免，只能通过增大缓存行来减少（一次加载更多数据）。

```
// 第一次访问 a[0]，该缓存行尚未加载
sum += a[0];   // compulsory miss
```

### 2. 容量缺失（Capacity Miss）

缓存大小不足以容纳程序的工作集（working set），导致之前加载过的缓存行被淘汰后又被重新访问。

```
// 工作集大小为 256 KB，而 L1 只有 32 KB
// 虽然有很多重复访问，但缓存装不下全部
for (int i = 0; i < LARGE; i++)
    for (int j = 0; j < LARGE; j++)
        a[i][j] *= 2;
```

### 3. 冲突缺失（Conflict Miss）

由于缓存组织方式的限制（后面会讲直接映射和组相联），多个地址会竞争同一个缓存行位置。即使缓存还有剩余空间，也会因为映射冲突而替换。

```
// 两个地址映射到同一缓存位置，互相驱逐
for (int i = 0; i < N; i += 4096)
    sum += a[i];    // conflict misses due to stride
```

## 缓存性能指标

### 命中率（Hit Rate）

```
Hit Rate = 命中次数 / 总访问次数
Miss Rate = 1 - Hit Rate
```

主流 CPU 的 L1 命中率通常在 90%–99% 之间。L2 命中率约 80%–95%。

### 平均内存访问时间（AMAT）

回顾上一节：

```
AMAT = HitTime + MissRate × MissPenalty
```

### 缺失率与缺失惩罚的关系

如果 Miss Penalty 很大（比如要从 DRAM 加载），即使 Miss Rate 只有 1%，对性能的影响也很大：

```
HitTime = 1 ns, MissRate = 1%, MissPenalty = 100 ns
AMAT = 1 + 0.01 × 100 = 2 ns   → 性能减半
```

## 缓存行大小的权衡

选择缓存行大小需要权衡：

| 缓存行大小 | 优点 | 缺点 |
|-----------|------|------|
| **小（16–32 B）** | 空间利用率高，减少碎片。冷缺失时不必加载无用数据。 | 空间局部性差的程序受益小；Tag 存储开销比例大。 |
| **大（64–128 B）** | 空间局部性好；Tag 比例小。 | 如果程序频繁访问不相邻的数据，会浪费带宽和缓存空间。 |

现代 CPU 的选择：几乎所有通用 CPU 的 L1 都是 64 B 缓存行。部分大型机 / HPC 芯片使用 128 B。

**实际例子**：遍历一个 64 字节的数据结构 vs 指向 64 字节的链表：

```
// 数组：空间局部性好，一次缓存行加载 8 个 int
for (i = 0; i < 1000000; i++) sum += arr[i];

// 链表：空间局部性差，每次加载的缓存行只有 4 字节有用
while (node) { sum += node->val; node = node->next; }
```

数组遍历的缓存缺失率远低于链表遍历。

## 关键概念

- **缓存行**：数据传输的最小单位，通常 64 B
- **Hit / Miss**：缓存是否包含请求数据
- **三种缺失**：冷缺失（不可避免）、容量缺失（缓存不够大）、冲突缺失（映射限制）
- **AMAT**：量化缓存对性能的影响
- **缓存行大小**：权衡空间局部性收益与存储效率

## 参考文献

- Hennessy, J. L. & Patterson, D. A., *Computer Architecture: A Quantitative Approach*, 6th ed., Chapter 2.1: The Basics of Caches.
- Hennessy, J. L. & Patterson, D. A., *Computer Organization and Design: The Hardware/Software Interface*, 5th ed., Chapter 5.1: Introduction to Caches.
- Drepper, U., "What Every Programmer Should Know About Memory", Red Hat, 2007. Section 3.1: Cache Organization.
- Intel Corporation, *Intel 64 and IA-32 Architectures Optimization Reference Manual*, Section 2.1.3: Cache Hierarchy.
