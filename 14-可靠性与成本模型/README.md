# 14 — 可靠性与成本模型

> 芯片不仅要知道“怎么算、怎么造”，还要回答“为什么会坏、为什么贵”。本模块从电迁移、热循环、软错误与老化出发，经过良率、die 成本、封装测试，最后把一切折算成 $/GPU-hour 与 $/token。所有寿命与成本数字都是工程估算，不构成采购、报价或验收依据。

---

## 本模块内容

| 笔记 | 主题 | 核心问题 |
|------|------|---------|
| 01 | **电迁移** | Black 方程如何把电流密度、温度与互连寿命联系起来 |
| 02 | **热循环与机械应力** | CTE 失配如何把温度循环变成焊点、TSV 与界面疲劳 |
| 03 | **软错误与 SER/FIT** | 粒子翻转如何计量，ECC 与位交错能挡到什么程度 |
| 04 | **老化：BTI、HCI、TDDB** | 晶体管如何退化，老化 guardband 从哪里来 |
| 05 | **良率模型** | 面积、缺陷密度与缺陷分布如何决定 die 良率 |
| 06 | **Die 成本与 NRE** | 每颗合格 die 怎么算，芯粒为什么可能更便宜 |
| 07 | **封装与测试成本** | CoWoS、HBM、KGD 与四道测试关卡如何进入 BOM |
| 08 | **AI 芯片 TCO** | 从 BOM 到 $/GPU-hour、$/token 的完整折算 |

## 前置知识

- [12 半导体器件与 CMOS 电路](../12-半导体器件与CMOS电路/)：MOSFET、Vth、栅介质、功耗与可靠性物理的语言
- [13 工艺制造与先进封装](../13-工艺制造与先进封装/)：BEOL、工艺节点、芯粒与 2.5D/3D 封装
- [11-03 功耗与散热](../11-系统分析与性能工程/notes/03-power-thermal.md)：TDP、结温、热阻与 DVFS
- [11-08 训练系统硬件预算](../11-系统分析与性能工程/notes/08-end-to-end-case.md)：MFU、GPU-hours 与大模型训练的系统账

## 建议学习方式

1. 先读 01–04，建立“失效物理”的直觉：电迁移、热机械、软错误、老化是四类不同的问题。
2. 再读 05–07，把物理量换成钱：良率 → die 成本 → 封装测试 BOM。
3. 最后读 08，把 BOM 折算成 $/GPU-hour 和 $/token，并与 11-08 的端到端案例对照。
4. 动手跑 `code/python/` 下的三个脚本，改参数做敏感性分析；所有输出只用于理解量级。
5. 读 `papers/01-black-electromigration.md`，理解一个经验公式如何被用了几十年、又在哪里失效。

## 本模块代码

| 文件 | 内容 |
|------|------|
| `python/yield_sim.py` | 给定面积、D0 与团簇参数，比较 Poisson、Murphy、负二项良率曲线 |
| `python/die_cost.py` | 从晶圆价格、毛 die 数、良率与 NRE 计算每颗合格 die 成本 |
| `python/tco_model.py` | 把 BOM、功耗、利用率与电价折算为 $/GPU-hour 与 $/token |

## 关键产出

- [ ] 能用 Black 方程做电流/温度加速因子的量级估算，并说清 `n` 与 `Ea` 的不确定性
- [ ] 能解释 CTE 失配、Coffin–Manson 与 DNP 公式分别回答什么问题
- [ ] 能把 SER（FIT/Mbit）换算成芯片级 FIT，并判断 ECC 是否够用
- [ ] 能区分 BTI、HCI、TDDB 的触发条件与缓解手段
- [ ] 能用四种良率模型估算大 die 的经济性，并解释面积弹性 `1 + A·D0`
- [ ] 能拆出一颗 AI 加速卡的 BOM，并算出 $/GPU-hour 与 $/token
- [ ] 能说清芯片侧成本模型与集群侧 TCO 的边界

## 参考文献

- Black, J. R. “Electromigration—A Brief Survey and Some Recent Results.” *IEEE Transactions on Electron Devices*, 1969. — Black 方程与电迁移综述。
- JEDEC. *JEP122H: Failure Mechanisms and Models for Semiconductor Devices*, 2016. — 失效机制、加速模型与可靠性认证的行业基线。
- JEDEC. *JESD89B: Measurement and Reporting of Alpha Particle and Terrestrial Cosmic Ray Induced Soft Errors*, 2021. — SER 测试与外推方法。
- Hennessy, J. L., & Patterson, D. A. *Computer Architecture: A Quantitative Approach*, 6th ed., Morgan Kaufmann, 2019. — 第 1 章，IC 成本、良率与产量摊销框架。
- Barroso, L. A., Clidaras, J., & Hölzle, U. *The Datacenter as a Computer*, 3rd ed., Morgan & Claypool, 2018. — 数据中心 TCO、PUE 与利用率。
- TSMC. *CoWoS Technology* and *2024 Annual Report*, 2024–2025. — 先进封装面积、产能与成本口径（公开估算）。
- Williams, T. W., & Brown, N. C. “Defect Level as a Function of Fault Coverage.” *IEEE Transactions on Computers*, 1981. — 测试覆盖率与缺陷逃逸。
