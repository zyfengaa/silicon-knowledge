# 12 — 半导体器件与 CMOS 电路

> 从电子和空穴出发，理解 MOSFET、CMOS 门、延迟与功耗，再把器件约束一路追到标准单元、SRAM 和芯片微架构。

---

## 本模块内容

| 笔记 | 主题 | 核心问题 |
|------|------|---------|
| 01 | **半导体、载流子与 PN 结** | 电子/空穴、掺杂、耗尽区与内建电场：半导体为什么能导电，PN 结为什么单向导电？ |
| 02 | **MOSFET 如何工作** | 栅控沟道、三个工作区、体效应、亚阈值与栅电容：一个栅压如何控制电流？ |
| 03 | **短沟道效应与 Dennard 缩放的终结** | Vth 滚降、DIBL、漏电与 60 mV/dec 下限：为什么缩小不再自动变快？ |
| 04 | **FinFET、GAA 与后平面晶体管** | 三面/四面栅、有效沟道宽度、宽度量子化与 CFET：栅极如何包住沟道？ |
| 05 | **CMOS 反相器与静态 CMOS 逻辑** | VTC、噪声容限、β 比、NAND/NOR 与传输门：开关如何变成逻辑？ |
| 06 | **门延迟、RC 与逻辑努力** | RC/Elmore、g/h/p、FO4 与中继器：一条组合路径到底有多快？ |
| 07 | **动态功耗、静态功耗与能量** | αCV²f、漏电、DVFS、能量-延迟积与暗硅：每次操作要花多少电？ |
| 08 | **从晶体管到微架构** | 全栈映射、PPA 三角、SRAM/NoC/Tensor Core 约束：器件物理如何塑造芯片架构？ |

## 前置知识

- [01 数字逻辑基础](../01-数字逻辑基础/)：布尔代数、CMOS 门与触发器的逻辑抽象；本模块会把“门”还原成晶体管和物理约束。
- 基础物理与电路（电压、电流、电容、指数函数）即可，不要求先修半导体物理。

## 建议学习方式

1. 按 01 → 02 → 03 的顺序读，先建立“载流子 → 沟道 → 短沟道”的因果链，不急着记公式。
2. 用 05/06 的手算例子（VTC、FO4、逻辑努力）做一遍纸笔推导，再运行 `code/python/` 下的脚本对照曲线。
3. 读 07 时把 SPECS §1 的 TDP 和 §7 的 Vdd/Vth 代入功耗公式，感受“电压不降”对功耗密度的影响。
4. 最后读 08，把 01–07 的器件/电路结论映射到模块 03/04/06/11 的流水线、乱序、Tensor Core 与暗硅问题。
5. 选做：完成 `exercises/12-devices-q.md`，并读 `papers/01-dennard-scaling.md` 对照原始论文。

## 本模块代码

| 文件 | 内容 |
|------|------|
| `python/mosfet_iv.py` | 绘制长沟道 nMOS 的输出特性与转移特性，标注线性区/饱和区边界和亚阈值斜率 |
| `python/cmos_vtc.py` | 用平方律模型扫描 CMOS 反相器 VTC，计算 VM、VIL/VIH 与噪声容限 |
| `python/power_model.py` | 计算动态/静态功耗、DVFS 的 P–V–f 关系与能量-延迟积 |
| `python/logic_effort.py` | 计算多级路径的 G/B/H/F、最优级数与逐级延迟 |

运行方式（Python 3.10+，仅依赖 `numpy` 与 `matplotlib`）：

```bash
cd 12-半导体器件与CMOS电路/code/python
python mosfet_iv.py
python cmos_vtc.py
python power_model.py
python logic_effort.py
```

脚本使用 `matplotlib.use("Agg")`，图片输出到脚本同目录；参数是教学示例，不代表任何具体 PDK。

## 关键产出

- [ ] 能解释 PN 结的内建电场、耗尽区与单向导电，并说出结电容和温度对漏电的影响。
- [ ] 能根据 Vgs/Vds 判断 MOSFET 工作区，写出平方律电流并说明体效应和短沟道修正。
- [ ] 能解释 Dennard 缩放的假设、60 mV/dec 下限，以及 2005 年前后电压/频率为何停住。
- [ ] 能画出 CMOS 反相器 VTC，定义 VM、VIL/VIH、NMH/NML，并解释 β 比的作用。
- [ ] 能用逻辑努力估算路径延迟和 FO4，能拆解动态/静态功耗并解释 DVFS 与暗硅。
- [ ] 能把器件约束传导到 SRAM 密度、乱序窗口、NoC 和 Tensor Core 尺寸，做 PPA 取舍。

## 参考文献

- Dennard, R. H. et al. "Design of Ion-Implanted MOSFET's with Very Small Physical Dimensions." *IEEE Journal of Solid-State Circuits*, 1974.
- Weste, N. H. E., & Harris, D. *CMOS VLSI Design: A Circuits and Systems Perspective* (4th ed.). Addison-Wesley, 2010.
- Rabaey, J. M., Chandrakasan, A., & Nikolic, B. *Digital Integrated Circuits: A Design Perspective* (2nd ed.). Prentice Hall, 2003.
- Sze, S. M., & Ng, K. K. *Physics of Semiconductor Devices* (3rd ed.). Wiley, 2007.
- Taur, Y., & Ning, T. H. *Fundamentals of Modern VLSI Devices* (2nd ed.). Cambridge University Press, 2009.
- IRDS. *International Roadmap for Devices and Systems: More Moore*, 2023–2024.
- *Silicon Knowledge 硬件规格基线（SPECS.md）* §1、§7 — TDP、Vdd/Vth、亚阈值摆幅与器件路线图的统一口径（[SPECS](../SPECS.md)）。
