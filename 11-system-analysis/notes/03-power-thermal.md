# 03 — 功耗与散热

> 功耗和散热是制约现代处理器性能的最根本因素。从 Dennard Scaling 的终结到"暗硅"的出现，功耗墙驱动了整个计算机体系结构在过去十五年的变革——从提高单核频率转向多核和领域专用加速。

---

## 1. 功耗基础

### 1.1 功耗方程

CMOS 电路的总功耗由两项组成：

```
P_total = P_dynamic + P_static
```

#### 动态功耗 (Dynamic Power)

```
P_dynamic = α · C · V² · f

其中:
α = 活动因子 (0-1, 信号每周期翻转的概率)
C = 负载电容 (由晶体管尺寸和连线决定)
V = 电源电压
f = 时钟频率
```

**关键关系**：动态功耗与电压的**平方**成正比，与频率成正比。

#### 静态功耗 (Static / Leakage Power)

```
P_static = V · I_leak

I_leak ≈ I_subthreshold + I_gate + I_junction

其中:
I_subthreshold: 亚阈值漏电流 (晶体管关断不完全)
I_gate: 栅极漏电流 (栅氧化层变薄导致)
I_junction: 源/漏-衬底结漏电流
```

随着工艺节点微缩，栅极漏电流剧增。在 28nm 以下，静态功耗已成为不可忽视的部分。

### 1.2 功耗分配

典型高性能 CPU 的功耗分布（~3GHz, 28nm）：

```
各单元的功耗占比:
┌──────────────┬──────┐
│ ALU/FPU      │ 15%  │  ← 真正做"有用"计算的
│ 寄存器文件    │ 10%  │
│ L1 / L2 cache│ 25%  │
├──────────────┼──────┤
│ 取指/译码    │ 10%  │  ← 控制开销
│ 乱序执行逻辑  │ 15%  │
│ 分支预测      │  5%  │
│ 重排/提交    │ 10%  │
├──────────────┼──────┤
│ 时钟树       │ 10%  │
└──────────────┴──────┘
```

**观察**：真正做"有用计算"的单元只占总功耗的一小部分——大量功耗消耗在控制逻辑和数据搬运上。

---

## 2. TDP 与散热设计

### 2.1 TDP (Thermal Design Power)

TDP 指散热系统需要能够处理的最大功耗，通常不等于实际功耗：

```
TDP ≥ 散热器能力 ≥ 平均功耗 ≥ 大部分时间的实际功耗
```

| 处理器 | TDP (W) | 制程 | 核心数 |
|--------|---------|------|--------|
| Intel Core i9-13900K | 125 (253 PL2) | Intel 7 | 24 |
| AMD Ryzen 9 7950X | 170 (230) | TSMC 5nm | 16 |
| NVIDIA A100 | 400 | TSMC 7nm | 6912 CUDA |
| NVIDIA H100 | 700 | TSMC 4nm | 18432 CUDA |
| Apple M2 Max | ~45 | TSMC 5nm | 12 |

### 2.2 散热方案

| 方案 | 最大散热能力 | 成本 | 适用场景 |
|------|-------------|------|---------|
| 被动散热 | ~5-10W | 低 | 嵌入式、手机 |
| 风冷 (散热片 + 风扇) | ~100-300W | 低-中 | 桌面、服务器 |
| 水冷 (AIO) | ~200-500W | 中 | 高性能桌面 |
| 水冷 (循环) | ~500-2000W | 高 | 数据中心 |
| 浸没式冷却 | ~2000W+ | 极高 | 超算 |
| 液氮/液氦 | 不限 | 极高 | 极限超频 |

---

## 3. DVFS (Dynamic Voltage and Frequency Scaling)

### 3.1 基本原理

DVFS 是在运行时动态调整电压和频率以平衡性能和功耗的技术：

```
P ∝ V² × f

降低电压 20% → 功耗降低 (0.8)² × 0.8 = 0.512 → ~49% 功耗降低
降低电压 20% → 频率降低 20% → 性能降低 20%

收益: 20% 性能损失 → 50%+ 功耗节省
```

### 3.2 实际实现

```
性能状态 (P-states):
P0: 最高频率 (标称电压)
P1: 较低频率 (降低电压)
...
Pn: 最低频率 (最低工作电压)

睡眠状态 (C-states):
C0: 活跃 (指令执行)
C1: HALT (停止时钟)
C2: Stop-Clock (关闭 PLL)
C3: Sleep (关闭 cache)
C6: Deep Sleep (保存上下文, 关闭电源)
```

### 3.3 电压-频率关系

```
频率 f ∝ (V - V_threshold) / V  (近似线性)

关键约束:
1. 所需电压随频率线性增长
2. 功耗随电压平方增长
3. 过高的频率需要过高的电压 → 功耗剧增

这就是为什么超频的功耗收益非常差:
从 4GHz 超到 4.5GHz → 频率 +12.5%
但电压可能需要从 1.2V 升到 1.35V → 功耗 (+12.5%) × (+12.5%)² ≈ +42%
```

---

## 4. Dark Silicon

### 4.1 现象

随着工艺微缩，晶体管的密度按摩尔定律增长，但功耗密度不再按 Dennard scaling 降低：

```
Dennard Scaling (黄金时代, ~1975-2005):
每代工艺 (-30% 尺寸):
- 晶体管密度: +2×
- 电压: -0.85×
- 电容: -0.85×
- 频率: +1.4×
- 每晶体管功耗 (动态): V² × f × α ~ (0.85)² × 1.4 × 0.85 ≈ 0.86×
= 总功耗: 0.86 × 2 = 1.72× ???

实际上 Dennard Scaling 假设每面积功耗基本不变:
(0.85)² × 1.4 ≈ 1.01  → 差不多不变

Dennard Scaling 终结后 (2005+):
- 电压无法再按比例降低 (V_th 无法降低)
- 晶体管密度继续 2×/代
- 但功耗密度不再降低
- → Dark Silicon
```

**Dark Silicon**：在给定的 TDP 约束下，不能同时为所有晶体管供电。芯片上必须有一部分区域处于"暗"（关闭）状态。

### 4.2 影响

```
假设:
- 每代晶体管密度 2×
- 每代单晶体管功耗不变 (Dennard 失效)
- TDP 不变

那么每代 ~50% 的晶体管必须处于"暗"状态
→ 只能使用一半的晶体管!
```

| 节点 | 可用比例 | 说明 |
|------|---------|------|
| 45nm (2008) | ~80% | Dennard 刚结束，影响较小 |
| 32nm | ~60% | |
| 22nm | ~40% | |
| 14nm | ~25% | |
| 7nm | ~15% | 大部分晶体管必须关闭 |
| 5nm | ~10% | >

### 4.3 架构应对

Dark Silicon 驱动的架构变革：

```
1. 多核 (但不是非常多核)
   - 不可能将所有晶体管都做成高性能核心
   - 部分作为 L2/L3 cache → 面积大但不太耗电

2. 专用加速器
   - 相同功耗下, ASIC 比 CPU 核心高效 10-100×
   - 在有限的功耗预算内做更多"有用的"计算

3. 近阈值计算 (Near-Threshold Computing)
   - 降低电压到接近阈值 → 大幅降低功耗
   - 但频率也大幅降低
   - 适合可大量并行的负载

4. 3D 堆叠
   - 在垂直方向扩展
   - 每个 die 可以有不同的电压/频率/散热
```

---

## 5. 功耗分析实例

### 5.1 GPU 功耗分析

```
NVIDIA H100 (700W TDP)
├── 计算核心: ~350W (50%)
│   ├── SM + Tensor Core: ~280W
│   └── 寄存器/L1: ~70W
├── HBM 内存: ~150W (21%)
│   ├── HBM2e 访问: ~100W
│   └── HBM 控制器: ~50W
├── 片上互联: ~70W (10%)
│   └── NVLink + 片内总线
├── 时钟: ~50W (7%)
└── 其它: ~80W (12%)
    └── PCIe, 内存控制器, 各类接口
```

### 5.2 数据中心 PUE

```
PUE (Power Usage Effectiveness) = 总能耗 / IT 设备能耗

理想 PUE = 1.0 (全部能耗用于计算)
典型数据中心 PUE = 1.2 - 1.6 (20-60% 额外用于冷却、配电等)
最优数据中心 PUE ≈ 1.04 (Google, 液冷)

以 H100 集群 (10,000 卡, 700W TDP):
- 总计算功耗: 700W × 10000 = 7MW
- 考虑 CPU / 网络 / 存储: ~10MW
- PUE 1.2: 总功耗 = 12MW
- 全年: 12MW × 8760h = 105,120 MWh
- 电费: ~$0.08/kWh → $8.4M/年
```

---

## 参考文献

1. Hennessy, J. L., & Patterson, D. A. (2019). *Computer Architecture: A Quantitative Approach* (6th ed., Chapter 1: Fundamentals). Morgan Kaufmann.
2. Esmaeilzadeh, H., et al. (2011). "Dark Silicon and the End of Multicore Scaling." *ISCA 2011*.
3. Dennard, R. H., et al. (1974). "Design of Ion-Implanted MOSFET's with Very Small Physical Dimensions." *IEEE Journal of Solid-State Circuits*.
4. Horowitz, M. (2014). "Computing's Energy Problem (and What We Can Do About It)." *ISSCC 2014*.
5. Borkar, S., & Chien, A. A. (2011). "The Future of Microprocessors." *Communications of the ACM*, 54(5).
6. Le, H. P. (2012). "Designing Processors for Power Efficiency." *PhD Dissertation, Stanford University*.
7. Shalf, J. (2020). "The Future of Computing Beyond Moore's Law." *Philosophical Transactions of the Royal Society A*, 378(2166).
