# 05-05 TLB

## 为什么需要 TLB

现代操作系统使用**虚拟内存**（Virtual Memory），每个进程拥有独立的虚拟地址空间。CPU 发出的所有地址都是虚拟地址，需要转换为物理地址才能访问主存。

地址转换的步骤通常是查**页表**（Page Table）——一个存储在内存中的多层次数据结构。查一次页表可能需要多次内存访问（x86-64 的 4 级页表需要 4 次内存读）。如果每次地址转换都查页表，性能会灾难性下降。

**TLB（Translation Lookaside Buffer）** 是一个专门缓存页表项（Page Table Entry, PTE）的小型高速缓存。

```
虚拟地址 ──→ [TLB 查找] ──命中──→ 物理地址 ──→ 缓存/内存
               │
             缺失
               │
               ↓
         [页表遍历] ──→ 物理地址 + 更新 TLB
```

TLB 的核心思想：利用**时间和空间局部性**，页表项一旦被查询，很可能在不久的将来再次被查询。

## TLB 的组织方式

TLB 通常是**全相联**或**高度组相联**的小型缓存（通常 32–1024 项）。

| CPU | L1 TLB (指令/数据) | L2 TLB (统一) |
|-----|-------------------|--------------|
| Intel Skylake | 64 项 (ITLB), 64 项 (DTLB) | 1536 项, 8-way |
| AMD Zen 4 | 72 项 (ITLB), 72 项 (DTLB) | 4096 项, 16-way |
| ARM Cortex-X2 | 48 项 (L1 ITLB), 48 项 (L1 DTLB) | ~2048 项, 5-way |

**TLB 项的内容**：

```
┌──────────┬──────────┬──────────┬──────┬──────┐
│ 虚拟页号 │ 物理页号 │ 有效位 │ 权限 │ 其他 │
└──────────┴──────────┴──────────┴──────┴──────┘
```

- **虚拟页号（VPN）**：用于匹配的 key
- **物理页号（PFN）**：转换结果
- **有效位**：该 TLB 项是否有效
- **权限位**：读/写/执行权限，用户态/内核态

## TLB 命中与缺失

### TLB Hit

虚拟地址的页号在 TLB 中找到匹配项 → 快速获得物理地址。

**代价**：通常 1–2 个周期。

### TLB Miss

虚拟地址的页号不在 TLB 中 → 需要遍历页表。

**硬件页表遍历（Hardware Page Walk）**（x86-64, ARMv8）：

MMU 中的专用硬件自动遍历多级页表，加载 PTE 并填充 TLB。

```
x86-64 4KB 页的 4 级页表遍历:
  CR3 → PML4 → PDP → PD → PT → 物理页
  需要 4 次内存访问（每级一次）
```

如果相关 PTE 已经在 L1/L2/L3 缓存中，遍历延迟约 10–30 ns；如果全部缺在 DRAM 中，延迟约 200–400 ns（数百个周期）。

**软件页表遍历**（部分 RISC-V 实现）：

当 TLB Miss 时，硬件触发异常（exception），操作系统内核软件遍历页表。这种方式设计更简单，但慢于硬件遍历。

### TLB Miss 为何比普通缓存 Miss 代价更大

| 事件 | 延迟 |
|------|------|
| L1 缓存 Miss（在 L2 命中） | ~10 ns |
| TLB Miss（页表遍历，PTE 在 L3 命中） | ~30 ns |
| TLB Miss（全部 DRAM 访问） | ~300 ns |
| TLB Miss + 页表项不在 DRAM（缺页中断 → 磁盘 I/O） | ~数百万 ns |

一次 TLB Miss 可能触发 4 次内存访问（多级页表遍历），代价远高于一次缓存 Miss。

## TLB Reach

**TLB Reach** 指 TLB 能够覆盖的虚拟地址空间总大小：

```
TLB Reach = TLB 项数 × 页面大小
```

示例：

```
TLB 64 项, 4 KB 页 → Reach = 256 KB
TLB 64 项, 2 MB 页 → Reach = 128 MB
```

如果程序的工作集（working set）大于 TLB Reach，TLB 会频繁 Miss，称为 **TLB Thrashing**。

## 大页（Huge Pages）

增大页面大小是提升 TLB Reach 的直接方法：

| 页面大小 | 俗称 | x86-64 页表级别 |
|---------|------|----------------|
| 4 KB | 标准页 | PT（Page Table） |
| 2 MB | 大页 | PD（Page Directory）→ 跳过 PT |
| 1 GB | 超大页 | PDP（Page Directory Pointer）→ 跳过 PD + PT |

**大页的优点**：
- 同样数量的 TLB 项覆盖更大的地址空间
- 减少页表层数（2 MB 页只需 3 级，1 GB 页只需 2 级）
- 减少 TLB Miss

**大页的缺点**：
- 内部碎片（分配 2 MB 但只用了几 KB）
- 操作系统支持需要额外的配置（hugetlbfs / transparent huge pages）

**典型应用**：数据库、HPC、虚拟化场景显著受益于大页。

## TLB 与缓存的关系

虚拟地址经过 TLB 转换后得到物理地址，再访问缓存：

```
虚拟地址 → [TLB] → 物理地址 → [L1/L2/L3 缓存] → 数据
```

这里涉及一个设计选择：缓存的 Tag 使用虚拟地址（VIVT）还是物理地址（PIPT）？

- **VIVT (Virtually Indexed, Virtually Tagged)**：快，但同义词问题（多个虚拟地址映射到同一物理地址）
- **PIPT (Physically Indexed, Physically Tagged)**：不存在同义词问题，但要等 TLB 转换后才能读 Tag——慢
- **VIPT (Virtually Indexed, Physically Tagged)**：多数现代 CPU 的选择。用虚拟地址的 Index（低位，不经过 TLB）快速选组，用物理 Tag 确认命中

## 关键概念

- **TLB**：地址转换专用缓存，加速虚拟→物理地址映射
- **TLB Miss**：代价远大于缓存 Miss，可能触发多级页表遍历
- **TLB Reach**：TLB 能覆盖的地址空间 = 项数 × 页大小
- **大页**：增大 TLB Reach 的有效手段
- **VIPT**：TLB 与缓存的协同工作方式

## 参考文献

- Hennessy, J. L. & Patterson, D. A., *Computer Architecture: A Quantitative Approach*, 6th ed., Section 2.3: Virtual Memory and TLBs.
- Hennessy, J. L. & Patterson, D. A., *Computer Organization and Design: The Hardware/Software Interface*, 5th ed., Section 5.4: Virtual Memory.
- Intel Corporation, *Intel 64 and IA-32 Architectures Software Developer's Manual*, Volume 3A, Chapter 4: Paging.
- ARM Limited, *ARM Architecture Reference Manual ARMv8-A*, Chapter D5: The AArch64 Virtual Memory System Architecture.
- Bhattacharjee, A. & Lustig, D., *Architectural and Operating System Support for Virtual Memory*, Morgan & Claypool, 2017.
