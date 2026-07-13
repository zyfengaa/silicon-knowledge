# 05-06 虚拟内存

## 虚拟内存抽象

虚拟内存（Virtual Memory）是操作系统与硬件（MMU）共同提供的一种抽象，让每个进程拥有一个独立的、连续的、大小为 2^n 的虚拟地址空间。

```
进程 A 虚拟地址空间        物理内存         进程 B 虚拟地址空间
┌─────────────┐          ┌──────────┐       ┌─────────────┐
│    代码     │──┐       │          │  ┌────│    代码     │
├─────────────┤  │   ┌───┤ 物理页 0 │──┘    ├─────────────┤
│    堆      │  ├──►│   ├──────────┤       │    堆      │
├─────────────┤  │   └───┤ 物理页 1 │       ├─────────────┤
│    栈      │──┘       ├──────────┤──┐    │    栈      │
└─────────────┘          │ 物理页 2 │  └────└─────────────┘
                         └──────────┘
```

**关键好处**：
- **隔离**：进程不能访问其他进程的内存
- **保护**：可以对不同页面设置读/写/执行权限
- **简化链接**：所有程序可以使用相同的地址布局（如 0x400000 起始）
- **交换**：不常用的页面可以被换出到磁盘

## 页表（Page Table）

页表是将虚拟地址转换为物理地址的核心数据结构。虚拟地址空间被划分为**页（Page）**，物理内存被划分为相同大小的**页帧（Page Frame）**。页表的每一项（PTE, Page Table Entry）记录了虚拟页到物理页帧的映射。

### 单级页表的问题

```
虚拟地址空间: 48 bits, 页大小: 4 KB
→ 页数: 2^48 / 2^12 = 2^36 = 68,719,476,736 页
→ 每项 8 字节 → 页表大小: 约 512 GB
```

每个进程维护 512 GB 的页表不可能——解决方案是**多级页表**。

## 多级页表（x86-64 的 4 级页表）

x86-64 使用 4 级页表，每级负责地址的一部分：

```
虚拟地址 (48-bit)
┌────────┬────────┬────────┬────────┬──────────┐
│  PML4  │  PDP   │   PD   │   PT   │  偏移量  │
│  9 bit │  9 bit │  9 bit │  9 bit │  12 bit  │
└────────┴────────┴────────┴────────┴──────────┘
```

**查询流程**：

1. **PML4**：CR3 寄存器指向 PML4（Page Map Level 4）表的物理地址。用 VPN[47:39] 索引 PML4 表，得到 PDP 表的物理地址
2. **PDP**：用 VPN[38:30] 索引 PDP（Page Directory Pointer）表，得到 PD 表的物理地址
3. **PD**：用 VPN[29:21] 索引 PD（Page Directory）表，得到 PT 表的物理地址
4. **PT**：用 VPN[20:12] 索引 PT（Page Table）表，得到物理页帧号
5. **偏移量**：物理页帧号 + 原地址低 12 位偏移 → 最终物理地址

```
CR3 → [PML4] → [PDP] → [PD] → [PT] → 物理页帧 + 偏移 = 物理地址
```

**多级页表的节省**：未使用的地址范围不需要分配页表。PML4 表只需要 512 项（4 KB），未使用的 PML4 项指向的空表可以不分配。

### x86-64 PTE 的字段

```
63          52 51  50   ...   12 11  10   9   8   7  6  5  4  3  2  1  0
┌──────────────┬────┬──────────┬──┬────┬───┬───┬───┬──┬──┬──┬──┬──┬──┬──┐
│   物理地址   │XD  │  保留    │  │ PAT │ D │ A │  │  │PS│  │R │U │W │P │
│   (高 40 bit)│    │          │  │     │   │   │  │  │  │  │W │S │/ │  │  │
└──────────────┴────┴──────────┴──┴────┴───┴───┴──┴──┴──┴──┴──┴──┴──┴──┘
```

**主要字段**：

| 位 | 名称 | 含义 |
|----|------|------|
| 0 | P (Present) | 页面是否在物理内存中 |
| 1 | R/W (Read/Write) | 0 = 只读, 1 = 读写 |
| 2 | U/S (User/Supervisor) | 0 = 仅内核态, 1 = 用户态可访问 |
| 4 | PWT (Page Write-Through) | 页级缓存写策略控制 |
| 5 | PCD (Page Cache Disable) | 禁止该页被缓存 |
| 6 | A (Accessed) | 硬件置位：该页被访问过 |
| 7 | D (Dirty) | 硬件置位：该页被写入过 |
| 63 | NX (No-Execute) | 禁止在该页执行代码（XD bit） |

## 页表遍历与 TLB

多级页表的每次遍历通常需要 **4 次内存访问**。如果每次地址转换都要遍历，程序会慢 4 倍以上。这是 TLB 存在的原因（见 05-05）。

**TLB Miss 处理流程**：

1. 硬件 MMU 自动遍历页表（x86, ARM）
2. 逐级读取页表项，检查 P（Present）位
3. 如果某级 P 位为 0 → 触发缺页异常 → OS 处理
4. 遍历完成后 PTE 写入 TLB

## 缺页中断（Page Fault）

当访问的页面在物理内存中不存在时：

1. MMU 检测到 PTE 的 P（Present）位为 0
2. MMU 触发 **Page Fault 异常**
3. OS 的缺页中断处理程序接管：
   - **有效缺页**：对应的文件已在磁盘上（如代码段）→ 从磁盘读入物理内存
   - **匿名缺页**：未映射文件的页面（堆、栈）→ 分配物理页面并清零
   - **COW（Copy-On-Write）**：fork 后父子进程共享页面，写时复制
   - **访问违规**：进程访问了没有权限的地址 → 发送 SIGSEGV

缺页中断的代价极其昂贵（毫秒级，数百万个 CPU 周期），远比 TLB Miss 或缓存 Miss 严重。

## 页面置换算法

当物理内存满时，需要选择页面换出到磁盘：

| 算法 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| FIFO | 先进先出 | 简单 | Belady 异常 |
| LRU | 最近最少使用 | 效果好 | 硬件实现复杂 |
| Clock（Second Chance） | 近似 LRU（利用 A 位） | 效果好，实现简单 | — |
| LFU | 最少使用频率 | 避免"有些页面很热" | 实现复杂，效率一般 |

Linux 使用**页面回收机制**（PFRA, Page Frame Reclaim Algorithm），核心是双 Clock 算法，兼顾活跃页面和不活跃页面。

## 大页（Huge Pages）

已在 05-05 中介绍。补充：在 x86-64 的 4 级页表中，2 MB 大页使用 PD 项直接指向 2 MB 物理页（跳过 PT 级），1 GB 大页使用 PDP 项直接指向 1 GB 物理页（跳过 PD 和 PT 级）。

```
PS (Page Size) bit = 1 表示该级页表项直接是一个大页映射
```

**启用方式**：
- Linux: `hugetlbfs` 显式配置，或 Transparent Huge Pages（THP）自动启用
- Windows: Large Pages API
- 数据库：PostgreSQL / MySQL 常配置启用大页

## 关键概念

- **虚拟内存**：为每个进程提供独立、连续的地址空间抽象
- **多级页表**：节省内存的数据结构，x86-64 使用 4 级
- **PTE 字段**：Present / R/W / U/S / A / D / NX 等
- **缺页中断**：访问不在物理内存的页面的处理流程
- **页面置换**：物理内存不足时选择换出页面的算法
- **大页**：减少页表层级和 TLB Miss 的有效手段

## 参考文献

- Hennessy, J. L. & Patterson, D. A., *Computer Architecture: A Quantitative Approach*, 6th ed., Section 2.3: Virtual Memory.
- Hennessy, J. L. & Patterson, D. A., *Computer Organization and Design: The Hardware/Software Interface*, 5th ed., Section 5.4: Virtual Memory.
- Intel Corporation, *Intel 64 and IA-32 Architectures Software Developer's Manual*, Volume 3A, Chapter 4: Paging.
- Bovet, D. P. & Cesati, M., *Understanding the Linux Kernel*, 3rd ed., Chapter 2: Memory Addressing.
- McKusick, M. K. et al., *The Design and Implementation of the FreeBSD Operating System*, 2nd ed., Chapter 5: Memory Management.
- The Linux Kernel documentation, Documentation/admin-guide/mm/transhuge.rst (Transparent Huge Pages).
