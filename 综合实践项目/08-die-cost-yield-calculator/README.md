# 项目 08 — Die 成本与良率计算器

> 从晶圆价格、die 面积、缺陷密度与封装测试出发，算出每颗合格 die / 每个合格封装单元的成本，并做敏感性分析与 chiplet 对比。

## 目标

- 把"面积变大为什么成本超线性上升"拆成每片毛 die 数、良率、封装与 NRE 四本账。
- 实现 Poisson、Murphy 与负二项三种良率模型，理解 D0 与缺陷团簇参数的影响。
- 计算单 die 与多 die 封装（chiplet / HBM）的成本，比较 monolithic 与 chiplet 的盈亏平衡点。
- 用龙卷风图（tornado plot）识别最敏感的成本杠杆，并给出可复现的工程估算。

## 前置知识

- [模块 13：工艺制造与先进封装](../../13-工艺制造与先进封装/notes/05-process-nodes.md)
- [Chiplet 与 UCIe](../../13-工艺制造与先进封装/notes/06-chiplet-ucie.md)、[2.5D/3D 先进封装](../../13-工艺制造与先进封装/notes/07-advanced-packaging.md)
- [模块 14：可靠性与成本模型](../../14-可靠性与成本模型/notes/05-yield-models.md)
- [Die 成本](../../14-可靠性与成本模型/notes/06-die-cost.md)、[封装与测试成本](../../14-可靠性与成本模型/notes/07-packaging-test-cost.md)
- [SPECS.md §7.3 封装与 §8.2 良率 / 成本基线](../../SPECS.md)（只作量级与公式口径，不是报价）

## 任务要求

**必做**

1. Python 3.10+，仅使用 `numpy` / `matplotlib`（绘图可 `Agg`）；输入用 JSON 或 YAML（若用 YAML 需在 README 说明依赖），输出 CSV 与 PNG。
2. 实现每片毛 die 数：`N_gross = π(D/2 − e)² / A − πD / √(2A)`，`A` 为 die 面积（mm²），`D` 为晶圆直径（默认 300 mm），`e` 为边缘排除宽度；同时实现一个独立的网格 / 圆内计数程序作为交叉验证。
3. 实现三种良率模型（`A` 换算为 cm²，`D0` 为 defects/cm²）：
   - Poisson：`Y = exp(−A·D0)`；
   - Murphy：`Y = ((1 − exp(−A·D0)) / (A·D0))²`；
   - 负二项：`Y = (1 + A·D0/α)^(−α)`，`α` 表示缺陷团簇程度。
4. 计算 `每颗合格 die 成本 = 每片晶圆价格 / (N_gross × Y)`；输出每 mm² 成本、良率与毛 die 数。
5. 支持多 die 封装，并显式选择两种口径之一：
   - **KGD（known-good die）**：只封装已测试合格的 die，使用每颗合格 die 成本，封装阶段再乘装配良率；
   - **非 KGD**：封装全部 die 后整体测试，使用未测试 die 成本，并除以封装内联合良率 `Y_joint = ΠY_i`。
   总成本包含 die、封装 / 中介层、HBM（按 `$/GB`）、测试与 NRE 摊销。
6. 计算 `每合格封装单元成本 = (die 成本项 + 封装 + HBM + 测试) / 装配良率 + NRE / 合格产量`，其中 die 成本项按第 5 步选择的口径计算，分母是"合格封装产量"。
7. 实现 monolithic vs 2-chiplet 对比：总面积相同，chiplet 有额外封装 / 互连成本与 DToD 开销；扫描年产量，求 NRE 与单位成本意义下的盈亏平衡点。
8. 敏感性分析：对 die 面积、D0、晶圆价格、封装成本、HBM 价格、年产量各扰动 ±20% 或 ±30%，输出龙卷风图与排序。

**可选扩展**

- 引入晶圆边缘部分 die、reticle 限制（26×33 mm 曝光场）与 2.5D 中介层面积上限。
- 加入测试覆盖率 / 逃逸率模型，区分"良率损失"与"测试成本"。
- 用蒙特卡洛抽样 D0 与价格分布，输出成本 P10 / P50 / P90。
- 加入 $/token 或 $/GPU-hour 的下游 TCO 折算（需说明所有假设）。

## 里程碑

- **M1 骨架**：毛 die 数 + Poisson 良率 + 单 die 成本；3 个手算案例通过。
- **M2 核心**：三种良率模型、多 die 封装、NRE 摊销；参数化输入。
- **M3 验证**：网格计数交叉验证、单调性与边界测试、chiplet 平衡点。
- **M4 报告**：敏感性、盈亏平衡、假设表与工程结论。

## 交付物

- `src/calculator.py`：公式与成本模型；`src/verify_geometry.py`：网格计数验证。
- `configs/`：单 die、2-chiplet、monolithic 等示例配置；`results/`：成本、良率、平衡点 CSV。
- `plots/`：良率 vs 面积、成本 vs 产量、龙卷风图、chiplet vs monolithic。
- `report.md`：公式推导、worked example、敏感性排序、所有假设与免责声明。

## 验收标准

- 3 个手算案例的成本、良率、毛 die 数与程序输出误差 < 0.1%（手算过程写入报告）。
- 300 mm 晶圆、10 组 die 面积的网格计数与解析毛 die 数相差 ≤ max(1 颗, 2%)；差异随面积变化的趋势可解释。
- 所有良率落在 `[0,1]`；`A → 0` 时良率 → 1；固定 D0 时良率随面积单调不增；负二项在 `α → ∞` 时趋近 Poisson。
- 在 `A·D0 = 1.8`、`α = 2` 的固定案例中，三种模型良率排序与公式计算一致（本项目案例下 Poisson < Murphy < 负二项），并解释原因。
- 多 die 封装的 KGD 与非 KGD 两种口径均可手算复现；装配良率为 1 时各自退化为对应的单 die 公式。
- chiplet 对比给出明确的平衡产量；低于 / 高于该产量时选择哪一方案有数据支持。
- 龙卷风图包含至少 5 个变量，排序与单变量重算一致；报告注明扰动范围。
- 所有成本数字标注年份、币种、"示例假设 / 工程估算，不构成采购、报价或验收依据"。

## 参考

- [良率模型](../../14-可靠性与成本模型/notes/05-yield-models.md)、[Die 成本](../../14-可靠性与成本模型/notes/06-die-cost.md)、[封装与测试成本](../../14-可靠性与成本模型/notes/07-packaging-test-cost.md)
- [Chiplet 与 UCIe](../../13-工艺制造与先进封装/notes/06-chiplet-ucie.md)、[先进封装](../../13-工艺制造与先进封装/notes/07-advanced-packaging.md)
- Hennessy & Patterson, *Computer Architecture: A Quantitative Approach*, 第 1 章（成本与良率）。
- [SPECS.md §8.2](../../SPECS.md)（Poisson / Murphy / 负二项公式与量级）
- ITRS / IRDS 关于良率模型与缺陷密度的公开资料（注明版本与年份）。

## 常见陷阱与口径

- **mm² 与 cm² 混用**是头号错误：`D0` 通常是 defects/cm²，而 die 面积常以 mm² 给出，先除以 100。
- 毛 die 数（gross）不是合格 die 数（good）；成本分母必须是 `N_gross × Y`，不是 `N_gross`。
- 边缘排除宽度 `e` 的单位是 mm，与晶圆直径一致；忽略 `e` 会高估毛 die 数。
- 多 die 封装把良率相乘隐含"缺陷独立"假设；若采用非 KGD 口径，联合良率 `ΠY_i` 会放大面积与 D0 的影响；KGD 口径则要另计已知合格 die 的测试成本，不能把两种口径混用。
- NRE 要按**合格产量**摊销；用总产量摊销会低估单位成本。
- 晶圆价格是区间量级，不能把示例值写成某代工厂的公开报价；成本数字必须带年份与假设。
- HBM 按 `$/GB` 是独立成本项，不要重复计入 die 面积或封装成本。
- 不要把"reticle 倍数"当作绝对面积上限；CoWoS 等方案有中介层尺寸与良率约束，需单独建模。
