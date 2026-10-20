#!/usr/bin/env python3
"""
文件名：  die_cost.py
描述：    300 mm 晶圆上每颗合格 die 的制造成本模型：毛 die 数近似公式、Poisson 良率、
         NRE 按产量摊销，并对 die 面积、缺陷密度和晶圆价格做敏感性分析。
运行：   python die_cost.py
输出：   die_cost_sensitivity.png，终端打印基准成本拆分与敏感性表。
参考：   [1] SPECS.md §8.2（每片 die 数公式、良率公式、晶圆价格量级）
         [2] de Vries, D. K. "Investigation of Gross Die per Wafer Formulas." IEEE TSM, 2005.
         [3] Hennessy & Patterson, Computer Architecture: A Quantitative Approach, 6th ed., 2019.
注意：   默认参数均为示例假设，不构成采购、报价或验收依据；实际排布受划片道、形状与掩模版限制。
"""
from pathlib import Path
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

# --------------------------- 默认参数（示例假设） ---------------------------
OUT_DIR = Path(__file__).resolve().parent
WAFER_DIAMETER_MM = 300.0        # 示例假设：主流 300 mm 晶圆
EDGE_EXCLUSION_MM = 3.0          # 示例假设：边缘排除 2–3 mm，取 3 mm
DIE_AREA_MM2 = 800.0             # 示例假设：大 die，接近一个掩模版视场
D0 = 0.1                         # 示例假设：defects/cm2，成熟工艺量级 0.1–1
WAFER_PRICE_USD = 17_000.0       # 示例假设：N5/5nm 级公开估算中值，不是报价
NRE_USD = 100_000_000.0          # 示例假设：掩模 + 设计 + 验证 + 封测开发
UNITS = 1_000_000.0              # 示例假设：全生命周期产量
TEST_COST_USD = 30.0             # 示例假设：基础探针/终测，封装另计
MM2_PER_CM2 = 100.0
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                     "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10, "legend.frameon": False, "lines.linewidth": 2.0})


# ------------------------------- 成本模型 -------------------------------
def gross_die_per_wafer(area_mm2=DIE_AREA_MM2):
    """N_gross ≈ π(D/2-e)²/A - πD/√(2A)，长度单位均为 cm，A 为 cm²。"""
    area_cm2 = area_mm2 / MM2_PER_CM2
    radius_cm = (WAFER_DIAMETER_MM / 2.0 - EDGE_EXCLUSION_MM) / 10.0
    diameter_cm = WAFER_DIAMETER_MM / 10.0
    return max(0.0, math.pi * radius_cm ** 2 / area_cm2
               - math.pi * diameter_cm / math.sqrt(2.0 * area_cm2))


def unit_cost(area_mm2=DIE_AREA_MM2, d0=D0, wafer_price=WAFER_PRICE_USD,
              units=UNITS, nre=NRE_USD, test_cost=TEST_COST_USD):
    """返回毛 die、良率、合格 die 与成本拆分；默认用 Poisson 良率。"""
    area_cm2 = area_mm2 / MM2_PER_CM2
    n_gross = gross_die_per_wafer(area_mm2)
    yield_p = math.exp(-area_cm2 * d0)
    n_good = n_gross * yield_p
    silicon = wafer_price / n_good if n_good > 0 else float("inf")
    nre_per_unit = nre / units if units > 0 else float("inf")
    return {"n_gross": n_gross, "yield": yield_p, "n_good": n_good,
            "silicon": silicon, "nre": nre_per_unit, "test": test_cost,
            "total": silicon + nre_per_unit + test_cost}


def print_assumptions(base):
    """打印基准假设、成本瀑布与敏感性表。"""
    print("Baseline: 300 mm wafer, example assumptions (not a quote)")
    print(f"  Die area              : {DIE_AREA_MM2:.0f} mm2")
    print(f"  Defect density D0     : {D0:.2f} defects/cm2 (Poisson yield)")
    print(f"  Wafer price           : ${WAFER_PRICE_USD:,.0f} / wafer")
    print(f"  NRE / lifetime units  : ${NRE_USD / 1e6:,.0f}M / {UNITS:,.0f}")
    print(f"  Base test cost        : ${TEST_COST_USD:,.0f} / die")
    print("-" * 58)
    print(f"  Gross die per wafer   : {base['n_gross']:.1f}")
    print(f"  Wafer-sort yield      : {base['yield']:.1%}")
    print(f"  Good die per wafer    : {base['n_good']:.1f}")
    print(f"  Silicon cost / good die: ${base['silicon']:,.0f}")
    print(f"  NRE amortization      : ${base['nre']:,.0f}")
    print(f"  Test (basic)          : ${base['test']:,.0f}")
    print(f"  Total / good die      : ${base['total']:,.0f}")
    print("\nSensitivity (one variable at a time; example assumptions)")
    print(f"{'Scenario':<12s} {'Value':>10s} {'Gross':>7s} {'Yield':>7s} "
          f"{'Silicon$':>9s} {'Total$':>8s} {'Delta':>7s}")
    print("-" * 66)
    scenarios = [("Baseline", f"A={DIE_AREA_MM2:.0f}", base)]
    for area in (400.0, 600.0, 1000.0):
        scenarios.append(("Die area", f"{area:.0f} mm2", unit_cost(area_mm2=area)))
    for d0 in (0.05, 0.2, 0.3):
        scenarios.append(("D0", f"{d0:.2f}", unit_cost(d0=d0)))
    for price in (12_000.0, 20_400.0, 25_000.0):
        scenarios.append(("Wafer price", f"${price / 1e3:.1f}k", unit_cost(wafer_price=price)))
    for label, value, row in scenarios:
        delta = row["total"] / base["total"] - 1.0
        print(f"{label:<12s} {value:>10s} {row['n_gross']:7.1f} {row['yield']:7.1%} "
              f"{row['silicon']:9,.0f} {row['total']:8,.0f} {delta:+7.1%}")


# ------------------------------- 绘图 -------------------------------
def plot_sensitivity(base):
    """三联图：面积、D0、晶圆价格对每颗合格 die 成本的影响。"""
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2))
    cases = [
        (axes[0], np.linspace(200.0, 1000.0, 120), DIE_AREA_MM2,
         lambda x: unit_cost(area_mm2=x), "Die area (mm2)", "Die area"),
        (axes[1], np.linspace(0.02, 0.30, 120), D0,
         lambda x: unit_cost(d0=x), "Defect density D0 (defects/cm2)", "D0"),
        (axes[2], np.linspace(10_000.0, 26_000.0, 120), WAFER_PRICE_USD,
         lambda x: unit_cost(wafer_price=x), "Wafer price ($/wafer)", "Wafer price"),
    ]
    for ax, xs, baseline_x, fn, xlabel, title in cases:
        costs = [fn(x)["total"] for x in xs]
        ax.plot(xs, costs, color=BLUE)
        base_y = fn(baseline_x)["total"]
        ax.scatter([baseline_x], [base_y], s=46, color=ORANGE, zorder=3)
        ax.annotate(f"${base_y:,.0f}", (baseline_x, base_y), textcoords="offset points",
                    xytext=(8, 10), fontsize=9, color=INK)
        ax.set(title=title, xlabel=xlabel, ylabel="Cost per good die ($)", ylim=(0, None))
    for ax in axes:
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
    fig.suptitle("Cost per good die: one-variable sensitivity "
                 "(Poisson yield; example assumptions, not a quote)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "die_cost_sensitivity.png", dpi=160)
    plt.close(fig)


def main():
    base = unit_cost()
    print_assumptions(base)
    plot_sensitivity(base)
    print("\nSaved: die_cost_sensitivity.png (script directory)")


if __name__ == "__main__":
    main()
