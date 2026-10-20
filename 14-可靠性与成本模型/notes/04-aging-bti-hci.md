# 04 — 老化：BTI、HCI 与 TDDB

> 晶体管不是“用不坏”的开关——长期偏压和温度会让 **阈值电压（Vth）** 漂移，高电场会让载流子注入界面，栅介质最终会被击穿，而 **BTI（偏置温度不稳定性）**、**HCI（热载流子注入）** 和 **TDDB（时间相关介质击穿）** 正是老化保护带（aging guardband）的三大来源，它们决定了芯片在寿命终点还能不能跑在标称频率和电压上。

---

## 为什么讲这个

先进工艺把栅介质做到几纳米等效厚度、把电源电压压到 0.6–1.2 V（`SPECS.md` §7.1），同时 AI 芯片又要 7×24 小时满载运行。按 `SPECS.md` §1，H100 SXM 的热设计功耗（Thermal Design Power, TDP）为 700 W、B200 为 1,000 W、B300/GB300 为 1,400 W；高功率意味着高结温，而 BTI、HCI、TDDB 的速率都随温度或电场上升。产品规格里写的“10 年寿命”目标（工程估算，不构成验收依据）不是自然保证，而是靠设计余量、工艺控制和加速实验外推出来的。

老化与电迁移、热循环、软错误的分工不同：

- **电迁移**（[01](01-electromigration.md)）发生在金属互连，失效形式是空洞/小丘；
- **热循环**（[02](02-thermal-mechanical-stress.md)）发生在封装和界面，失效形式是疲劳裂纹；
- **老化**（本篇）发生在晶体管/栅介质，失效形式是 Vth 漂移、驱动电流下降和栅介质击穿；
- **软错误**（[03](03-soft-errors.md)）是瞬态粒子翻转，不是磨损。

本篇只讨论晶体管级老化机制与寿命预算；封装级热机械失效、互连电迁移和系统级容错分别见对应笔记。机柜/集群层面的故障率统计不在本篇范围。

---

## 核心概念

### 1. 老化、guardband 与寿命终点

**老化（aging）** 是器件参数随时间不可逆或部分可逆地退化。设计上通常区分：

- **寿命起点（Beginning of Life, BOL）**：出厂时的参数；
- **寿命终点（End of Life, EOL）**：产品寿命目标（常见 5–10 年量级，具体由产品定义）时的最坏参数；
- **老化保护带（guardband）**：为保证 EOL 仍能满足时序/电压/良率而预留的余量。

老化保护带可以体现在多个地方：更高的标称电压、更慢的时钟、更保守的时序角（corner）、更大的静态随机存取存储器（Static Random Access Memory, SRAM）辅助电路、或运行时的自适应电压/频率调整。guardband 越大越安全，但会直接吃掉性能和能效——这就是为什么工艺厂和设计团队要花大量精力建模老化。

### 2. BTI：偏置温度不稳定性

**偏置温度不稳定性（Bias Temperature Instability, BTI）** 是栅极长期加偏压、同时处于较高温度时，界面陷阱生成和氧化层电荷俘获导致的 Vth 漂移。按器件类型分：

- **NBTI（Negative Bias Temperature Instability）**：pMOS 在负栅压、高温下，`|Vth|` 增大（阈值更负），驱动能力下降；
- **PBTI（Positive Bias Temperature Instability）**：nMOS 在正栅压、高温下，Vth 增大；在高介电常数（High-k）/金属栅工艺中尤其受关注。

BTI 的关键特征是**部分可恢复（recoverable）**：应力撤去后，部分陷阱会释放电荷，Vth 部分回弹。这给寿命测试带来麻烦——测量延迟、应力/恢复历史和占空比都会影响结果。常见的经验规律是：

```
ΔVth = A · t^n
```

`n` 通常在 **0.1–0.25** 量级（公开文献；反应—扩散模型与俘获/去俘获模型给出不同指数），`A` 与温度、栅压、工艺和器件尺寸有关。温度激活能不高（公开文献常给出 ~0.1 eV 量级），但因为 `Vth` 漂移会直接改变延迟和 SRAM 稳定性，即使几个 mV 到几十 mV 的漂移也可能吃掉可观的 guardband。

BTI 的影响包括：

- 逻辑路径延迟增加，尤其 pMOS 拉高路径；
- SRAM 的静态噪声容限（Static Noise Margin, SNM）和 `Vmin` 退化，限制低压工作；
- 模拟电路的失调、增益和匹配退化；
- 器件失配（mismatch）随老化增大。

缓解手段包括降低栅压/占空比、优化 High-k 界面、使用功函数工程、增大关键器件尺寸、在设计中预留老化余量，以及运行时通过体偏置/自适应电压补偿。

### 3. HCI：热载流子注入

**热载流子注入（Hot Carrier Injection, HCI）** 发生在高漏源电压 `Vds` 下：沟道中的载流子被强电场加速，获得高能量后撞击晶格（碰撞电离），产生电子—空穴对；部分高能载流子越过栅介质势垒，注入氧化层，形成界面态和 trapped charge。结果是 Vth 漂移、跨导 `gm` 和饱和电流 `Idsat` 下降。

HCI 的特点：

- 主要影响 nMOS（电子迁移率高、碰撞电离强），pMOS 也可能退化；
- 与 `Vds` 强相关，通常在短沟道器件、输入/输出（I/O）电路和高电压域更严重；
- 温度依赖较弱，甚至可能出现**低温更严重**（载流子平均自由程更长），与 BTI 的 Arrhenius 行为不同；
- 交流（AC）应力下有恢复/退化与频率相关的复杂行为，不能只用直流（DC）数据外推。

工艺上的缓解包括轻掺杂漏（LDD）、侧墙（spacer）、梯度结（graded junction）、降低 `Vds`、优化栅氧化层质量；设计上则靠电压域划分、I/O 器件选型和时序/电压 guardband。

### 4. TDDB：时间相关介质击穿

**时间相关介质击穿（Time-Dependent Dielectric Breakdown, TDDB）** 是栅介质在长期电场应力下形成导电通道、最终击穿的现象。其微观图像是：介质中的缺陷随机生成并累积，当缺陷连成贯穿介质的**渗流通路（percolation path）** 时，漏电急剧上升，发生软击穿或硬击穿。

TDDB 的统计通常用 **Weibull 分布（Weibull distribution）** 描述：

```
F(t) = 1 − exp[−(t/η)^β]
```

`η` 是特征寿命，`β` 是形状参数。TDDB 的面积效应很重要：栅面积越大，出现致命缺陷组合的概率越高，特征寿命越低。常用近似为 `η ∝ A^(-1/β)`；这就是为什么大面积的功率器件、大 SRAM 阵列和 I/O 器件需要单独评估 TDDB。

电压加速模型常见有三类：

- **E 模型**：`t_BD ∝ exp(−γ·E_ox)`；
- **1/E 模型**：`t_BD ∝ exp(G/E_ox)`；
- **幂律模型**：`t_BD ∝ V^(-n)`，公开文献常见 `n≈4–6` 量级。

不同模型在不同介质/电场区间适用，外推到低电场时差异可能很大；工程上必须用工艺数据选择并验证模型，不能把某个 `n` 当作普适常数。High-k/金属栅的引入改变了介质层结构（界面层 + High-k 层），击穿统计和软击穿行为更复杂，需要专门的可靠性评估。

### 5. 机制对比

| 机制 | 触发条件 | 主要影响 | 缓解手段 |
|------|----------|----------|----------|
| NBTI | pMOS 负栅压 + 高温 | Vth 绝对值增大、延迟增加、SRAM Vmin 退化 | 降低栅压/占空比、界面工程、尺寸/余量 |
| PBTI | nMOS 正栅压 + 高温（High-k） | Vth 增大、驱动下降 | High-k 界面优化、功函数工程、电压控制 |
| HCI | 高 `Vds`、碰撞电离 | Vth 漂移、gm/Idsat 下降 | LDD/spacer、降低 Vds、I/O 器件选型 |
| TDDB | 高栅电场 + 时间 | 栅漏电上升、软/硬击穿 | 介质厚度/等效氧化层厚度（Equivalent Oxide Thickness, EOT）、面积/电压控制、缺陷控制 |
| 电迁移 | 高电流密度 + 温度 | 互连空洞/小丘、开路/短路 | 电流密度规则、通孔冗余、Blech 豁免 |
| 热疲劳 | 温度循环/CTE 失配 | 焊点/TSV/界面裂纹 | 材料匹配、underfill、结构/几何优化 |

### 6. 关键参数速查

| 参数 | 典型值/范围 | 口径 | 来源（年份） |
|------|-------------|------|--------------|
| NBTI 时间指数 `n` | 0.1–0.25 | `ΔVth ∝ t^n`，依模型/工艺 | 公开文献量级 |
| NBTI 温度激活能 | ~0.1 eV 量级 | 低于 TDDB，但 Vth 漂移影响直接 | 公开文献量级 |
| HCI 温度依赖 | 弱，可能低温更严重 | 与 BTI 的 Arrhenius 行为不同 | 公开文献量级 |
| TDDB 电压指数 `n` | 4–6 | 幂律模型；E/1/E 模型另计 | 公开文献量级 |
| TDDB 激活能 | ~0.6–0.9 eV（SiO2 量级） | 介质与电场区间相关 | 公开文献量级 |
| 电源电压 `Vdd` | 0.6–1.2 V | 随节点与电压域变化 | `SPECS.md` §7.1 |
| 结温上限 `Tj` | 85–105 °C | 依器件与寿命预算 | [11-03 热设计](../../11-系统分析与性能工程/notes/03-power-thermal.md) |
| 寿命目标 | 5–10 年量级 | 产品规格定义，非普适值 | 工程惯例；示例假设 |

### 7. 寿命预算与加速模型

老化的寿命外推通常用 **Arrhenius 模型（Arrhenius model）** 描述温度加速：

```
AF_T = exp[(Ea/k) · (1/T_use − 1/T_stress)]
```

电压加速常用幂律或指数形式：

```
AF_V = (V_stress / V_use)^n        或
AF_V = exp[γ · (V_stress − V_use)]
```

总加速因子近似为 `AF = AF_T × AF_V`（假设机制不变、无交互作用）。示例（以 TDDB 类高温机制为例；工程估算，不构成验收依据）：`Ea=0.7 eV`、`T_use=85 °C (358 K)`、`T_stress=125 °C (398 K)`，温度项约 `exp(2.28)≈9.8`；若 `n=5`、`V_stress=1.2 V`、`V_use=1.1 V`，电压项约 `(1.2/1.1)^5≈1.54`；合计约 15×。也就是说，1,000 小时的高温高压实验粗略对应 15,000 小时使用时间，约 1.7 年。这个例子只展示量级，真实外推还要考虑恢复效应、占空比、面积和失效分位数（percentile）。

寿命预算的常见做法：

1. 确定产品寿命目标（如 10 年）和最坏使用剖面（温度、电压、占空比）；
2. 用加速实验提取每个机制的 `Ea`、`n`、`β` 和分布；
3. 外推到使用条件（use condition），取保守分位数（percentile）（而不是中位数）；
4. 把 BTI/HCI/TDDB/EM/热疲劳的退化叠加到 EOL 参数；
5. 用老化感知静态时序分析（Static Timing Analysis, STA）、SRAM margin 分析和系统遥测（telemetry）验证 guardband；
6. 留出工艺/批次/模型不确定性余量。

---

## 关键图示

### 图 1：Vth 漂移随应力时间的幂律

```
ΔVth
  │            /
  │          /
  │        /      斜率 = n（log–log）
  │      /
  │    /
  └──────────────→ t_stress（对数轴）
     短应力        长应力
```

在双对数坐标下，`ΔVth = A·t^n` 是一条直线。不同温度对应不同截距/斜率；若高温数据明显偏离同一条线，说明机制发生了变化（例如从界面陷阱生成转为介质击穿前兆）。

### 图 2：三种机制的物理位置

```
        Gate
   ┌──────────────┐
   │  High-k /    │  ← TDDB：缺陷累积 → 渗流通路
   │  界面层       │  ← BTI：界面陷阱 + 氧化层电荷
   ├──────────────┤
   │  沟道         │  ← HCI：高能载流子从漏端注入
   └──────────────┘
     Source   Drain
                ↑
           高 Vds / 碰撞电离
```

BTI 是“整条沟道上方”的偏压/温度效应，HCI 集中在漏端高场区，TDDB 是栅介质本身的击穿。三者的空间位置不同，因此缓解手段也不同。

### 图 3：寿命外推流程

```
加速实验（高 T / 高 V）
        │
        ▼
提取 Ea、n、β、η
        │
        ▼
AF = AF_T × AF_V
        │
        ▼
外推到 use condition
        │
        ▼
取保守分位数（percentile） → EOL 参数 → guardband
```

每一步都带不确定性；外推的价值取决于模型是否在实验窗口内被验证，而不是取决于公式看起来多漂亮。

---

## 深入理解

### 1. BTI 的恢复效应与测量陷阱

BTI 的部分恢复意味着“应力—测量”之间的延迟会显著影响读数。快速测量（on-the-fly）和传统“stress-measure-stress”方法可能给出不同的 `ΔVth`；如果测量延迟很长，部分退化已经恢复，寿命会被高估。工程上需要：

- 固定测量延迟和温度；
- 区分永久性/可恢复分量；
- 在接近实际占空比的 AC 条件下验证；
- 用多个应力电压/温度点提取模型参数。

这也是为什么不同厂商/论文给出的 NBTI 寿命可能差很多——测试方法不同，不能直接比较。

### 2. HCI 的电压依赖与 AC 效应

HCI 的退化率强烈依赖 `Vds`，常用衬底电流 `Isub` 或 `Isub/Id` 作为监测指标。交流（AC）应力下，载流子注入与退火可能交替发生，退化与频率、占空比和上升/下降时间有关；简单地把直流（DC）寿命按占空比线性缩放并不可靠。对高速 I/O、SerDes 和高电压域，HCI 往往是比 BTI 更紧的约束。

### 3. TDDB 的统计与面积缩放

TDDB 是“最弱环节”问题：栅面积越大，越可能包含一条致命缺陷链。Weibull 分布的形状参数 `β` 反映缺陷分布的分散程度；面积缩放 `η ∝ A^-1/β` 让我们可以从一个小面积测试结构外推到大面积阵列，但前提是缺陷是随机且独立的。若存在工艺缺陷团簇、边缘效应或局部薄化，面积缩放会失效。

软击穿（soft breakdown）后器件可能仍能工作，但漏电和噪声上升；硬击穿则直接失效。可靠性评估要区分两者，不能只统计“完全开路”。

### 4. 老化保护带（guardband）的量化

假设某个关键路径在 BOL 有 `T_BOL` 的延迟，EOL 因 BTI/HCI 增加 `ΔT_age`，则设计必须满足：

```
T_BOL + ΔT_age + 工艺/电压/温度余量 ≤ T_clk
```

如果 `ΔT_age` 对应 3–5% 的延迟增加（示例量级，具体依路径和工艺），设计要么降低频率、要么提高电压、要么在电路/架构上补偿。提高电压会加速老化，形成“电压—老化—再提高电压”的恶性循环；因此现代片上系统（System on Chip, SoC）常用自适应电压/频率、体偏置、老化传感器和片上遥测来动态调整 guardband。

### 5. 先进工艺与系统协同

- **High-k/金属栅**：改善了栅控和漏电，但引入了 PBTI、界面层击穿和电荷俘获（charge trapping）等新问题；
- **FinFET/GAA**：鳍式场效应晶体管（FinFET）与环绕栅极（GAA）的三维沟道改善了静电控制，但自热（self-heating）更严重，局部温度升高会加速 BTI/TDDB；GAA 的纳米片厚度和界面质量是关键；
- **低电压/近阈值**：BTI 的 `ΔVth` 在低电压下占比更大，SRAM `Vmin` 退化更敏感；
- **AI 芯片**：长时间高利用率、功率波动和高温叠加，老化预算必须按实际工作负载而不是“平均功耗”来算；
- **系统层**：遥测、动态电压频率调整（Dynamic Voltage and Frequency Scaling, DVFS）、电压/频率保护和预测性维护可以缓解老化，但它们的可靠性本身也要纳入预算；SoC 还会用老化传感器动态调整 guardband。

系统/集群层面的故障统计与运维策略不在本篇范围；本篇只提供晶体管级机制与寿命预算的物理基础。

---

## 总结

BTI 是偏压 + 温度导致的 Vth 漂移，NBTI 影响 pMOS、PBTI 影响 nMOS，且具有部分恢复性；HCI 是高 `Vds` 下热载流子注入造成的界面/氧化层损伤，温度依赖弱、漏端最严重；TDDB 是栅介质缺陷累积形成渗流通路，最终软/硬击穿。三者共同决定老化 guardband，寿命外推依赖 Arrhenius/电压加速模型和保守分位数（percentile）。所有寿命、加速因子和退化数字都是工程估算，不构成验收依据；真实设计必须用工艺数据和加速实验校准。

---

## 参考文献

1. JEDEC. *JEP122H: Failure Mechanisms and Models for Semiconductor Devices*, 2016. — BTI、HCI、TDDB 等失效机制与模型的行业参考。
2. JEDEC. *JEP148: Reliability Qualification of Semiconductor Devices Based on Physics of Failure Risk and Opportunity Assessment*, 2004. — 基于失效物理的鉴定与寿命外推框架。
3. Schroder, D. K. "Negative Bias Temperature Instability: Road to Cross in Deep Submicron Silicon Semiconductor Manufacturing." *Journal of Applied Physics*, 2003. — NBTI 机制、测量与寿命外推的经典综述。
4. Hu, C., et al. "Hot-Electron-Induced MOSFET Degradation—Model, Monitor, and Improvement." *IEEE Transactions on Electron Devices*, 1985. — HCI 物理、衬底电流监测与工艺缓解的经典论文。
5. McPherson, J. W. "Time Dependent Dielectric Breakdown Physics—Models Revisited." *Microelectronics Reliability*, 2012. — TDDB 渗流模型、Weibull 统计与电压加速的综述。
6. Weste, N. H. E., & Harris, D. *CMOS VLSI Design: A Circuits and Systems Perspective*, 4th ed., Addison-Wesley, 2010. — 可靠性、老化与设计余量章节。
7. Rabaey, J. M., Chandrakasan, A., & Nikolic, B. *Digital Integrated Circuits: A Design Perspective*, 2nd ed., Prentice Hall, 2003. — 器件退化、噪声容限与低功耗设计背景。
8. IRDS. *International Roadmap for Devices and Systems: More Moore*, 2023–2024. — High-k、FinFET/GAA 与可靠性路线图口径。
