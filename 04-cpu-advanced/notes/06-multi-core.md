# 06 — 多核与缓存一致性（Multi-Core & Cache Coherence）

## 概述

## 为什么需要多核？

### "单核时代"的终结

2005 年左右，CPU 设计遇到了微观和物理瓶颈：

**1. 功耗墙（Power Wall）**

```
功耗 ∝ 电容 × 电压² × 频率
```

- Dennard scaling（每一代晶体管尺寸缩小 30%，功耗降低 50%）在 2005 年左右失效
- 晶体管阈值电压降低接近物理极限，漏电流急剧增加
- 频率提升导致功耗呈立方增长

**具体数据**：
- Pentium 4 (Prescott, 2004)：3.8 GHz，130W TDP
- 若按趋势继续，10 GHz 处理器的功耗将接近核反应堆水平

**2. ILP 墙（ILP Wall）**

- 研究（Wall 1991, etc.）表明典型程序的 ILP 上限为 2 ~ 6
- 即使无限资源（无限 ROB、完美预测），也无法突破此上限
- 发射宽度超过 6 ~ 8 后收益极低

**3. 存储墙（Memory Wall）**

- 处理器性能年增长 ~55%
- 内存性能年增长 ~7%
- 差距每代扩大

### 多核的解决方案

多核通过多线程并行（Thread-Level Parallelism, TLP）绕过 ILP 限制：

- 每个核心独立执行线程
- 总吞吐量 ≈ 核心数 × 单核性能（理想情况）
- 相比于更宽的超标量，多核更节能高效

## 多核架构

### 基本结构

```
                    ┌──────────────────────┐
                    │      L3 缓存共享       │
                    └──┬────┬────┬────┬─────┘
                       │    │    │    │
                    ┌──┴──┐┌┴──┐┌┴──┐┌┴──┐
                    │Core0││Core1││Core2││Core3│
                    │L1 L2││L1 L2││L1 L2││L1 L2│
                    └─────┘└─────┘└─────┘└─────┘
                    ┌──────────────────────┐
                    │ 内存控制器 (MC)        │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴───────────┐
                    │      DRAM (主存)      │
                    └──────────────────────┘
```

每个核心拥有私有 L1/L2 缓存，共享 L3 缓存。

## 缓存一致性（Cache Coherence）

### 一致性问题

当多个核心各自拥有缓存时，同一个内存地址的数据可能同时出现在多个缓存中。如果一个核心修改了数据，其他核心必须看到修改后的值。

**核心问题**：保证所有核心对同一内存地址的视图一致。

```
// 初始：X = 0，X 在 Core0 和 Core1 的 L1 缓存中都有副本
Core0: X = 5;   // 只修改了 Core0 的 L1 缓存中的 X → Core1 仍看到 X = 0
Core1: print(X); // 输出 0 — 不一致！
```

### MESI 协议

MESI 是最经典的缓存一致性协议，定义了缓存行的四种状态：

| 状态 | 全称 | 该缓存行是否有效 | 其他核心是否有副本 | 与主存是否一致 |
|------|------|----------------|-----------------|--------------|
| **M** | Modified（修改） | 是 | 否（独占） | 否（被修改，最新值在此） |
| **E** | Exclusive（独占） | 是 | 否（独占） | 是（与主存一致） |
| **S** | Shared（共享） | 是 | 可能有 | 是（与主存一致） |
| **I** | Invalid（无效） | 否 | — | — |

### 状态转换

```
           读命中
     ┌────────────────────┐
     │                    │
     ▼                    │
   ┌─────┐   本地写     ┌─────┐
   │  E  │ ──────────→  │  M  │
   └──┬──┘             └──┬──┘
      │                   │
      │ 其他核读          │ 其他核读
      ▼                   ▼
   ┌─────┐             ┌─────┐
   │  S  │             │  S  │
   └──┬──┘             └──┬──┘
      │                   │
      │ 写（总线请求）     │ 写（总线请求）
      ▼                   ▼
    全部无效化          全部无效化
   ┌─────┐             ┌─────┐
   │ │  │ → 本地写 →   │  M  │
   └─────┘             └─────┘
```

#### 关键设计

**总线嗅探（Bus Snooping）**：

- 每个核心的缓存控制器"监听"总线上的读写事务
- 当本地缓存行被其他核心读取/写入时，做出相应状态转换
- 写入操作需要获得独占权限（Invalidate 其他所有副本）

**写命中的处理流程**：

```
Core0 写入在 L1 缓存中的 X（状态为 S）：
1. Core0 → 发送 Invalidate 请求到总线
2. Core1 → 将 X 对应缓存行标记为 I（Invalid）
3. Core1 → 发送 Ack
4. Core0 → X 状态变为 E（提升）
5. Core0 → 写入 X → 状态变为 M
```

### MOESI 和 MESIF 协议

| 协议 | 额外状态 | 作用 | 使用 |
|------|---------|------|------|
| MOESI | O (Owned) | 共享且被修改，主存副本过时 | AMD Opteron, ARM |
| MESIF | F (Forward) | 指定一个核心作为"转发响应者" | Intel Nehalem+ |

**O（Owned）态**：
- 数据被修改，但其他核心也可以共享读取
- 主存中的数据不是最新
- 拥有 O 态的核心有义务在总线上提供数据
- 好处：其他核心读时无需写回主存

**F（Forward）态**：
- 在多个 S 态副本中指定一个 Forwarder
- 当需要数据时，由 F 态核心响应，无需广播所有 S 态核心
- 减少总线流量

## 伪共享（False Sharing）

### 问题描述

伪共享是最常见的多核性能问题之一，发生在两个核心修改**不同变量**但这些变量位于**同一缓存行**中时。

```
// 缓存行大小 = 64 字节
// struct 中两个 int 恰好落在同一缓存行
struct data {
    int counter_a;   // Core0 只修改 counter_a
    int counter_b;   // Core1 只修改 counter_b
};

// 假设 struct 起始地址 = 0x1000
// counter_a 在 0x1000 (偏移 0)
// counter_b 在 0x1004 (偏移 4)
// 两者都在缓存行 [0x1000 - 0x103F] 内
```

**执行过程**：

```
Core0 递增 counter_a:
1. Core0: 加载缓存行 [0x1000 - 0x103F] → S
2. Core0: 写入 counter_a → 需要独占 → Invalidate Core1 的副本
3. Core1: 副本被 Invalidate

Core1 递增 counter_b:
4. Core1: 加载缓存行 [0x1000 - 0x103F] → 从 Core0 取数据
5. Core1: 写入 counter_b → 需要独占 → Invalidate Core0 的副本
6. Core0: 副本被 Invalidate

→ 每步都需要缓存行传输，性能严重下降！
```

这就像两个人在同一个房间（缓存行）里各自写自己的笔记。一个人要修改时，必须先把对方赶出去（Invalidate），对方要回来时必须敲门拿钥匙再从你手里抢走（重新加载）。他们实际上并不需要同一资源，却被物理布局强制共享。

### 性能影响

- 每次计数器递增需要 ~50 ~ 200 个周期（缓存一致性协议开销）
- 对比无伪共享：~1 个周期（寄存器内递增）
- 性能下降高达 **10× ~ 100×**

### 伪共享的检测

```bash
# Linux Perf: 检测缓存一致性缺失
perf stat -e cache-misses,cache-references,cache-miss-rate ./program

# Intel VTune / AMD uProf: 专门的"假共享分析"
# Valgrind: 使用 cachegrind 模拟器检查
```

### 伪共享的解决方案

**1. 缓存行填充（Cache Line Padding）**

```c
// 方案 1：在变量之间插入填充
struct data {
    int counter_a;
    char pad[60];        // 填充到 64 字节边界
    int counter_b;
    char pad2[60];       // 填充到 64 字节边界
};

// 方案 2：使用 alignas
struct alignas(64) padded_data {
    int counter_a;
    char pad[60];
    int counter_b;
};

// 方案 3：每个变量独立对齐到缓存行
struct __attribute__((aligned(64))) per_core_data {
    int counter;
};
struct per_core_data core0_data;
struct per_core_data core1_data;
```

**2. 线程本地存储（Thread-Local Storage）**

```c
// C11 的 _Thread_local
_Thread_local int counter;  // 每个线程有自己的计数器
```

**3. 使用分离的数据结构**

确保每个线程处理结构体拥有独立缓存行的数据（如数组中嵌入 padding）。

### 何时警惕 False Sharing？

- 多线程频繁写入同一结构体的不同字段
- 多线程的计数器在不同核心上递增
- 数组分块处理，但元素在内存中连续且很小（如字节数组）
- 开源库中 lock-free 的数据结构

## NUMA（Non-Uniform Memory Access）

### 架构对比

| 架构 | 特点 | 延迟 | 带宽 |
|------|------|------|------|
| UMA (Uniform) | 所有核心到所有内存延迟相同 | 统一 | 统一 |
| NUMA (Non-Uniform) | 本地内存快，远程内存慢 | 差别大 | 差别大 |

### NUMA 架构

现代多插槽（multi-socket）服务器普遍采用 NUMA：

```
Socket 0                     Socket 1
┌──────────────────┐        ┌──────────────────┐
│ Core0 Core1 ...  │        │ Core4 Core5 ...  │
│    L3 Cache      │        │    L3 Cache      │
│   Mem Controller │        │   Mem Controller │
└────────┬─────────┘        └────────┬─────────┘
         │                           │
         ▼                           ▼
    ┌──────────┐              ┌──────────┐
    │  本地内存  │              │  本地内存  │
    │  (Node 0) │ ←──── 互联 ───→│  (Node 1) │
    └──────────┘    (Infinity   └──────────┘
                    Fabric /
                    UPI / CXL)
```

### NUMA 延迟差异

假设：DDR5-4800，AMD EPYC 或 Intel Xeon：

| 访存位置 | 延迟（近似） | 带宽（近似） |
|---------|-------------|-------------|
| L1 缓存命中 | ~1 ns | 极高 |
| L2 缓存命中 | ~4 ns | 极高 |
| L3 缓存命中 | ~15 ns | 高 |
| 本地内存节点 | ~80 ~ 100 ns | ~50 ~ 70 GB/s |
| 远程内存节点 | ~140 ~ 200 ns | ~20 ~ 40 GB/s |
| 跨插槽远程 | ~180 ~ 300 ns | ~10 ~ 20 GB/s |

延迟差异可达 2× ~ 3× 甚至更多。

### NUMA 感知编程

**在 Linux 上查看 NUMA 拓扑**：

```bash
# 查看 NUMA 节点
numactl --hardware
# 示例输出：
# available: 2 nodes (0-1)
# node 0 cpus: 0 1 2 3
# node 0 size: 32768 MB
# node 1 cpus: 4 5 6 7
# node 1 size: 32768 MB
# node distances:
# node   0   1
#   0:  10  21
#   1:  21  10

# 查看进程的 NUMA 策略
cat /proc/self/numa_maps

# 查看页分配情况
numastat -p <pid>
```

**NUMA 感知的线程绑定**：

```c
// 使用 libnuma（GNU）
#include <numa.h>

// 将当前线程绑定到 node 0
struct bitmask *mask = numa_allocate_cpumask();
numa_bitmask_setbit(mask, 0);  // Core 0
numa_bind(mask);
numa_free_cpumask(mask);

// 在当前 node 上分配内存
void *p = numa_alloc_local(size);

// 或者在指定 node 上分配
void *p = numa_alloc_onnode(size, node_id);
```

**NUMA 友好的编程原则**：

1. **本地化分配**：每个线程访问的数据尽量在本地内存节点分配
2. **First-Touch 策略**：在 Linux 中，物理页在首次访问时分配。确保初始化线程和目标计算线程在同一 NUMA 节点上
3. **线程绑定**：将线程绑定到固定的核心，避免跨节点迁移
4. **避免频繁跨节点访问**：跨节点共享数据会通过互联引起额外延迟

## 多核性能优化核心原则

1. **最小化共享可写数据**：每个核心尽量访问私有数据
2. **对齐敏感数据**：使用缓存行对齐（64/128 字节）
3. **NUMA 感知**：数据分配在计算所在节点
4. **减少锁竞争**：粒度过大的锁 → 粗粒度串行化
5. **优化内存布局**：顺序访问优于随机访问，利用硬件预取

## 关键概念总结

- **多核驱动力**：功耗墙 + ILP 墙 + 存储墙
- **MESI 协议**：M（修改）、E（独占）、S（共享）、I（无效）
- **False Sharing**：不同变量同一缓存行导致的不必要一致性流量
- **NUMA**：非一致内存访问架构，本地/远程延迟差异
- **缓存行填充**：添加 padding 防止伪共享

## 思考题

1. 为什么 MESI 中 M 状态的行在被其他核心读时变为 S，而不是仍停留在 M？如果你设计一个协议保留 M 同时允许其他共享读，需要考虑什么？
2. False Sharing 的检测手段有哪些？为什么它在现代多核架构上依然是一个普遍问题？
3. 在 NUMA 架构上，如果一个线程需要访问另一个节点的数据，有哪些策略可以减少性能损失？
4. "First-Touch" 策略是什么？为什么内存页的初始化位置会影响 NUMA 性能？

## 参考文献

- Hennessy, J. L. & Patterson, D. A. *Computer Architecture: A Quantitative Approach*, 6th Edition, Chapter 5: Multiprocessors and Thread-Level Parallelism.
- Patterson, D. A. & Hennessy, J. L. *Computer Organization and Design*, Chapter 6: Multicore, Multiprocessors, and Clusters.
- Papamarcos, M. S. & Patel, J. H. "A New Cache Coherence Scheme for Shared-Memory Multiprocessors." *ISCA*, 1984.
- Laudon, J. & Lenoski, D. "The SGI Origin: A ccNUMA Highly Scalable Server." *ISCA*, 1997.
- Bolosky, W. J. & Scott, M. L. "False Sharing and Its Effect on Shared Memory Performance." *USENIX SEDMS*, 1993.
- AMD. *AMD64 Architecture Programmer's Manual: Volume 2 — System Programming*, Chapter 7: Multicore and NUMA.
