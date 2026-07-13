# 05-04 缓存策略

## 替换策略

当缓存已满且发生缺失时，需要选择一个缓存行**驱逐**（evict）以腾出空间。选择哪个行被替换的策略称为**替换策略（Replacement Policy）**。

### LRU（Least Recently Used）

**原理**：替换最久没有被访问的行。基于时间局部性——最近被访问过的数据更可能在将来再次被访问。

**优点**：命中率通常最高，能很好地适应各种访问模式。
**缺点**：硬件实现昂贵。对于 N 路组相联，需要记录 N 个行的相对访问顺序，需要 O(N²) 个比较器和 O(N log N) 个状态位。

```
访问序列: A B C D A B E
LRU 状态 (3-way):
  A → 最近使用 1, 其他 0
  B → B-A, ...
  E → E 替换最旧的 C (C 是最久未使用的)
```

**实现方式**：每组维护一个访问顺序链表/矩阵。4 路需要 6 位记录状态；8 路需要 28 位。

### 伪 LRU（Pseudo-LRU / Tree-Based PLRU）

**原理**：用二叉树记录每行的"被访问"状态。每个内部节点用一个 bit 指示下一次应该淘汰左子树还是右子树。

```
         ┌─┬─┐
         │ 0 │      ← 根节点: 0 = 走左子树, 1 = 走右子树
         └─┴─┘
        /     \
    ┌─┬─┐   ┌─┬─┐
    │ 0 │   │ 1 │  ← 内部节点继续分流
    └─┴─┘   └─┴─┘
   /    \   /    \
  A     B  C     D ← 叶子节点对应缓存行
```

**优点**：实现简单（4 路只需 3 bit，8 路只需 7 bit），性能接近 LRU。
**缺点**：在遍历较大工作集时可能比 LRU 略差。

**实际硬件**：Intel Core 系列 L2/L3 缓存使用近似 PLRU（称为按需伪 LRU）。

### 随机替换（Random）

**原理**：随机选一行驱逐。

**优点**：硬件极简（一个随机数生成器或计数器），没有状态开销。
**缺点**：可能随机驱逐即将被使用的行，命中率通常比 LRU 低 5–10%。

**适用场景**：当缓存容量远大于工作集时，随机替换的表现接近 LRU。

### FIFO（First-In, First-Out）

**原理**：替换最早加载到缓存的行，不考虑它是否被频繁访问。

**优点**：实现简单，循环队列即可。
**缺点**：存在"Belady 异常"（Belady's Anomaly）——增大缓存容量反而可能降低命中率。

## 替换策略对比

| 策略 | 命中率 | 硬件开销 | 适用场景 |
|------|-------|---------|---------|
| LRU | 最佳 | 高（N² 比较器） | 小型缓存（L1） |
| 伪 LRU | 接近 LRU | 低（N-1 bits） | 通用 CPU L2/L3 |
| 随机 | 一般 | 极低 | 大缓存，工作集适配 |
| FIFO | 较差 | 低 | 实时系统（可预测性） |

## 写策略

缓存不仅要处理读，还要处理写。写策略决定了写操作何时传播到下一级存储。

### Write-Through（写直达 / 写通）

每次写操作同时写入缓存和主存。

```
CPU → [写入缓存] + [立即写入内存]
```

**优点**：
- 缓存与内存始终一致（cache coherence 简单）
- 缺失时不需要写回（内存中永远是最新的）

**缺点**：
- 每次写操作都需要等内存写入完成（或通过写缓冲缓解）
- 内存带宽消耗大

**改进**：加写缓冲（Write Buffer）——CPU 将写请求放入缓冲后继续执行，内存异步写入。

### Write-Back（写回）

写操作只写入缓存，不立即更新内存。当该缓存行被驱逐时，才将其写回内存。

```
CPU → [写入缓存，标记脏位(dirty bit)]
     → 驱逐时：如果脏位=1，写回内存
```

**优点**：
- 写操作速度快（只写到缓存）
- 节省内存带宽（同一行多次修改只需一次回写）

**缺点**：
- 缓存与内存可能不一致
- 驱逐时要检查脏位，增加复杂度

**脏位（Dirty Bit）**：每行一个 bit，标记该行被修改过。1 = 已被写，驱逐时必须写回内存。

### Write-Allocate vs No-Write-Allocate

当写操作发生**缺失**时：

| 策略 | 行为 |
|------|------|
| **Write-Allocate（写分配）** | 先将该缓存行从内存加载到缓存，再修改缓存行 |
| **No-Write-Allocate（不写分配）** | 直接写入内存，不加载到缓存 |

**搭配使用**：
- **Write-Back 通常搭配 Write-Allocate**：既然要回写，不如先加载整行到缓存
- **Write-Through 通常搭配 No-Write-Allocate**：反正要写内存，直接写即可

## 实际 CPU 中的策略组合

| CPU | L1 写策略 | L1 替换 | L2/L3 写策略 | L2/L3 替换 |
|-----|----------|---------|-------------|-----------|
| Intel Core i7 (Skylake) | Write-Back | Pseudo-LRU | Write-Back | Pseudo-LRU |
| ARM Cortex-A78 | Write-Back | Pseudo-LRU | Write-Back | Pseudo-LRU |
| AMD Zen 4 | Write-Back | Pseudo-LRU | Write-Back | Pseudo-LRU |

## 关键概念

- **LRU**：理论上最优，但硬件成本随路数平方增长
- **伪 LRU**：实际中普遍采用的折中方案
- **Write-Back**：写快，省带宽，主流选择
- **Write-Through**：一致性简单，但写带宽开销大
- **脏位**：Write-Back 必须的辅助标记

## 参考文献

- Hennessy, J. L. & Patterson, D. A., *Computer Architecture: A Quantitative Approach*, 6th ed., Section 2.2: Cache Performance.
- Hennessy, J. L. & Patterson, D. A., *Computer Organization and Design: The Hardware/Software Interface*, 5th ed., Section 5.3: Cache Performance.
- Intel Corporation, *Intel 64 and IA-32 Architectures Optimization Reference Manual*, Section 2.1.4: Replacement and Write Policies.
- Al-Zoubi, H. et al., "Performance evaluation of cache replacement policies for the SPEC CPU2000 benchmark suite", *ACM SE'04*.
