# 项目 07 — CMOS 功耗与 VTC 实验

> 用 SPICE 实测反相器的电压传输特性、传播延迟与开关能量，把 `αCV²f`、噪声容限和能量-延迟权衡从公式变成曲线。

## 目标

- 通过 DC 扫描得到 CMOS 反相器 VTC，提取 `VM`、`VIL`、`VIH`、噪声容限与增益。
- 通过瞬态仿真测量 `tpHL`、`tpLH`、平均传播延迟及其对负载电容的依赖。
- 从电源电流积分得到每次开关的能量，与 `C_L·VDD²` 对比并解释短路功耗。
- 测量静态漏电随输入状态与温度的变化，理解动态 / 静态功耗的边界。

## 前置知识

- [MOSFET 如何工作](../../12-半导体器件与CMOS电路/notes/02-mosfet-operation.md)
- [CMOS 反相器与静态 CMOS 逻辑](../../12-半导体器件与CMOS电路/notes/05-cmos-inverter.md)
- [门延迟、RC 与逻辑努力](../../12-半导体器件与CMOS电路/notes/06-gate-delay-logic-effort.md)
- [动态功耗、静态功耗与能量](../../12-半导体器件与CMOS电路/notes/07-power-dynamic-static.md)
- [短沟道效应与 Dennard 缩放](../../12-半导体器件与CMOS电路/notes/03-short-channel-dennard.md)
- [SPECS.md §7 工艺与器件基线](../../SPECS.md)（只用于量级对照，不是 PDK 参数）
- 工具：[tools.md](../../tools.md) 中的 ngspice / LTspice 条目

## 任务要求

**必做**

1. 选定一套**公开可获取的器件模型**并固定版本：SkyWater sky130 PDK（标称 1.8 V）或 PTM 45 nm（标称 1.0 V）。记录模型文件来源、版本与校验和；不得混用不同工艺的模型和电压。
2. 搭建最小 CMOS 反相器网表：`Wn` 固定，`Wp/Wn` 取 1/2/2.5/3 扫描；`L` 取 sky130 的 0.15 µm 或 PTM 45 nm 的 0.045 µm（与所选模型一致）；负载 `C_L ∈ {5, 10, 20, 50} fF`。
3. **DC 实验**：在 `0 → VDD` 范围以 ≤ 5 mV 步长扫描 `Vin`，得到 VTC；提取 `VM`（`Vout = Vin`）、`VIL` / `VIH`（`dVout/dVin = −1` 的两个点）、`VOL`、`VOH`、增益与 `NMH = VOH − VIH`、`NML = VIL − VOL`。至少在标称、0.8×、0.6× VDD 三个电压下重复。
4. **瞬态实验**：输入为 0 → VDD → 0 脉冲，上升 / 下降时间固定（例如 10 ps），测量 50% 点的 `tpHL`、`tpLH` 与 `tpd = (tpHL + tpLH)/2`；对 4 个 `C_L` 各做一次，拟合 `tpd = t_int + R_drive·C_L`。
5. **能量实验**：对一次 0 → 1 输出跳变积分 `VDD · I_VDD(t)`，扣除同条件静态漏电基线，得到 `E_switch`；与 `C_L·VDD²` 比较，并估算短路功耗占比。说明一个完整 0→1→0 周期与单次跳变的区别。
6. **漏电实验**：在 `Vin = 0` 与 `Vin = VDD` 两种输入状态下测 `I(VDD)`；若模型支持温度，至少在 27 °C 与 125 °C 重复，报告比值与趋势。
7. **VDD 扫描**：在模型允许范围内取至少 5 个 VDD，报告 `tpd`、`E_switch` 与 `EDP = tpd × E_switch`，找出 EDP 最低点或解释为何单调。

**可选扩展**

- 101 级环形振荡器，测周期并换算 FO4 延迟。
- 加入互连线 RC 或扇出 4 的负载，比较逻辑努力预测与仿真。
- 用多个工艺角（TT/FF/SS）或温度角比较延迟与漏电。
- 扫描 `Wp/Wn` 使 `VM ≈ VDD/2`，解释迁移率差异。

## 里程碑

- **M1 骨架**：模型可加载、反相器 DC 仿真收敛、VTC 可导出。
- **M2 核心**：VIL/VIH/VM 与噪声容限提取；瞬态延迟测量。
- **M3 验证**：能量积分、漏电、VDD 扫描；与手算 / 解析模型对照。
- **M4 报告**：VTC、延迟-负载、能量-电压、EDP 图与设计结论。

## 交付物

- `netlists/`：DC、瞬态、漏电、VDD 扫描网表；`scripts/`：一键运行与数据提取脚本。
- `models/README.md`：模型名称、版本、来源 URL、校验和、允许的电压 / 温度范围。
- `results/`：VTC、延迟、能量、漏电原始数据 CSV；`plots/`：VTC、`tpd vs C_L`、`E vs VDD`、EDP。
- `report.md`：实验方法、参数、结果表、误差来源与"仿真非流片"声明。

## 验收标准

- 三个 VDD 下的 VTC 均单调下降，过渡区增益 `|dVout/dVin| > 1`，`NMH > 0` 且 `NML > 0`（标称电压下）。
- `tpd vs C_L` 线性拟合 `R² ≥ 0.99`；给出 `t_int` 与 `R_drive` 的数值和单位，并与手算 RC 量级对照。
- 在 `C_L = 20 fF` 时，积分得到的 `E_switch` 与 `C_L·VDD²` 相差 ≤ 25%；差值能用短路电流与输出扩散电容解释。
- VDD 降低时 `tpd` 增大、`E_switch` 减小；若 EDP 出现极小值，给出对应 VDD；若没有，解释扫描范围或模型限制。
- 漏电数据覆盖两种输入状态；有温度扫描时给出 125 °C / 27 °C 比值并与亚阈值趋势对照，无温度模型时明确声明。
- 网表、模型、脚本可复现；报告写明 ngspice 版本、`.tran` 最大步长与提取阈值。
- 所有结论标注"基于模型仿真，不代表真实硅片测量"。

## 参考

- [CMOS 反相器](../../12-半导体器件与CMOS电路/notes/05-cmos-inverter.md)、[功耗笔记](../../12-半导体器件与CMOS电路/notes/07-power-dynamic-static.md)
- Weste, N., & Harris, D. *CMOS VLSI Design: A Circuits and Systems Perspective*, 第 1–5 章。
- Rabaey, J. et al. *Digital Integrated Circuits: A Design Perspective*，反相器与功耗章节。
- [SkyWater sky130 PDK](https://github.com/google/skywater-pdk)、[PTM 模型](https://ptm.asu.edu/)
- [ngspice 手册](https://ngspice.sourceforge.io/docs.html)

## 常见陷阱与口径

- 1.8 V 的 sky130 与 1.0 V 的 PTM 不能混用；先记录标称电压，再决定扫描范围，避免把器件推出模型有效区。
- `VIL` / `VIH` 用单位增益点（斜率 −1）定义；用 10% / 90% 或固定电压点会得到不同噪声容限。
- 延迟必须在输出 50% VDD 处测；输入边沿过慢会显著改变延迟，必须固定 `tr` / `tf` 并写入报告。
- 能量要对**电源电流**积分，不是输出电流；否则漏掉短路功耗。积分窗口要覆盖完整跳变并扣除漏电基线。
- 单次 0→1 跳变的电源能量约为 `C_L·VDD²`；不要与一个完整周期的平均功耗 `αCV²f` 混淆，α 的口径要写清。
- 漏电强烈依赖输入状态与温度；只测 `Vin=0` 会低估或高估另一状态。
- `.tran` 最大步长要小于输入边沿的 1/10；否则波形和积分误差很大。
- 仿真得到的 45 nm / 130 nm 数字不是"某颗真实芯片"的实测值；报告必须限定为模型结果。
