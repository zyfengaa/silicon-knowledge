#!/usr/bin/env python3
"""
文件名：  tco_model.py
描述：    加速器板卡级 capex/opex 简化 TCO 模型：把购置成本、寿命、利用率、板卡功耗、
         电价与维护折算为 $/GPU-hour 与 $/token，并对利用率与电价做敏感性分析。
运行：   python tco_model.py
输出：   tco_sensitivity.png，终端打印成本拆分、$/GPU-hour、$/token 与敏感性表。
参考：   [1] SPECS.md §8.2（TCO 口径：capex + opex + 失效/运维，折算 $/GPU-hour、$/token）
         [2] Hennessy & Patterson, Computer Architecture: A Quantitative Approach, 6th ed., 2019.
边界：   仅芯片/板卡层，不含集群 PUE、制冷、网络、存储、厂房与现场失效成本；
         集群级 TCO 见 https://github.com/zyfengaa/why-ai-cluster/blob/main/README.md
注意：   所有参数均为示例假设，不构成采购、报价或验收依据。
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

# --------------------------- 默认参数（示例假设） ---------------------------
OUT_DIR = Path(__file__).resolve().parent
ACCELERATOR_CAPEX_USD = 30_000.0   # 示例假设：H100 级板卡，2024–2026 公开估算量级
LIFETIME_YEARS = 4.0               # 示例假设：折旧寿命 3–5 年
UTILIZATION = 0.70                 # 示例假设：有效训练/推理利用率
BOARD_POWER_W = 700.0              # 示例假设：板卡级功耗，不含整机与制冷
ELECTRICITY_USD_PER_KWH = 0.10     # 示例假设：工业电价
MAINTENANCE_RATE = 0.05            # 示例假设：每年维护/备件占 capex 比例
TOKENS_PER_SECOND = 1500.0         # 示例假设：推理吞吐（活跃时段）
HOURS_PER_YEAR = 8760.0
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                     "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10, "legend.frameon": False, "lines.linewidth": 2.0})


# ------------------------------- TCO 模型 -------------------------------
def tco_metrics(capex=ACCELERATOR_CAPEX_USD, power_w=BOARD_POWER_W,
                electricity=ELECTRICITY_USD_PER_KWH, utilization=UTILIZATION,
                lifetime=LIFETIME_YEARS, maintenance_rate=MAINTENANCE_RATE,
                tokens_per_s=TOKENS_PER_SECOND):
    """按年折算 capex/能耗/维护，返回 $/GPU-hour 与 $/token。"""
    annual_capex = capex / lifetime
    annual_energy = (power_w / 1000.0) * HOURS_PER_YEAR * utilization * electricity
    annual_maintenance = capex * maintenance_rate
    annual_total = annual_capex + annual_energy + annual_maintenance
    utilized_hours = HOURS_PER_YEAR * utilization
    per_gpu_hour = annual_total / utilized_hours
    return {"annual_capex": annual_capex, "annual_energy": annual_energy,
            "annual_maintenance": annual_maintenance, "annual_total": annual_total,
            "utilized_hours": utilized_hours, "per_gpu_hour": per_gpu_hour,
            "per_token": per_gpu_hour / (tokens_per_s * 3600.0),
            "energy_share": annual_energy / annual_total}


def print_tables(base):
    """打印基准拆分、利用率敏感性与电价敏感性。"""
    print("Accelerator board-level TCO (example assumptions, not a quote)")
    print(f"  Capex / lifetime      : ${ACCELERATOR_CAPEX_USD:,.0f} / {LIFETIME_YEARS:.0f} yr")
    print(f"  Board power           : {BOARD_POWER_W:.0f} W")
    print(f"  Electricity           : ${ELECTRICITY_USD_PER_KWH:.2f}/kWh")
    print(f"  Utilization           : {UTILIZATION:.0%}")
    print(f"  Maintenance           : {MAINTENANCE_RATE:.0%} of capex per year")
    print(f"  Throughput            : {TOKENS_PER_SECOND:,.0f} tokens/s (active)")
    print("-" * 60)
    print(f"  Annual capex          : ${base['annual_capex']:,.0f}")
    print(f"  Annual energy         : ${base['annual_energy']:,.0f} "
          f"({base['energy_share']:.1%} of annual cost)")
    print(f"  Annual maintenance    : ${base['annual_maintenance']:,.0f}")
    print(f"  Annual total          : ${base['annual_total']:,.0f}")
    print(f"  Utilized GPU-hours/yr : {base['utilized_hours']:,.0f}")
    print(f"  $/GPU-hour            : ${base['per_gpu_hour']:,.2f}")
    print(f"  $/token               : ${base['per_token']:.3e}")
    print(f"  $/1M tokens           : ${base['per_token'] * 1e6:,.2f}")
    print("\nSensitivity to utilization (electricity fixed at base price)")
    print(f"{'Utilization':>12s} {'Annual$':>10s} {'$/GPU-hour':>12s} {'$/1M tokens':>13s}")
    print("-" * 52)
    for u in (0.30, 0.50, 0.70, 0.85, 0.95):
        m = tco_metrics(utilization=u)
        print(f"{u:12.0%} {m['annual_total']:10,.0f} {m['per_gpu_hour']:12.2f} "
              f"{m['per_token'] * 1e6:13.2f}")
    print("\nSensitivity to electricity price (utilization fixed at base)")
    print(f"{'$/kWh':>8s} {'Annual$':>10s} {'$/GPU-hour':>12s} {'$/1M tokens':>13s} "
          f"{'Energy share':>13s}")
    print("-" * 66)
    for price in (0.05, 0.08, 0.10, 0.15, 0.25):
        m = tco_metrics(electricity=price)
        print(f"{price:8.2f} {m['annual_total']:10,.0f} {m['per_gpu_hour']:12.2f} "
              f"{m['per_token'] * 1e6:13.2f} {m['energy_share']:13.1%}")


# ------------------------------- 绘图 -------------------------------
def plot_sensitivity():
    """左：$/GPU-hour；右：$/1M tokens；三条线对应低/基准/高电价。"""
    utilization = np.linspace(0.20, 0.98, 120)
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.6))
    for price, color, label in ((0.05, BLUE, "$0.05/kWh"), (0.10, ORANGE, "$0.10/kWh (base)"),
                                (0.25, AQUA, "$0.25/kWh")):
        hours = [tco_metrics(electricity=price, utilization=u)["per_gpu_hour"]
                 for u in utilization]
        tokens = [tco_metrics(electricity=price, utilization=u)["per_token"] * 1e6
                  for u in utilization]
        axes[0].plot(utilization, hours, color=color, label=label)
        axes[1].plot(utilization, tokens, color=color, label=label)
    for ax, title, ylabel in ((axes[0], "Cost per GPU-hour", "$/GPU-hour"),
                              (axes[1], "Cost per million tokens", "$/1M tokens")):
        ax.set(title=title, xlabel="Utilization", ylabel=ylabel, ylim=(0, None))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.2f}"))
    base = tco_metrics()
    axes[0].scatter([UTILIZATION], [base["per_gpu_hour"]], s=46, color=ORANGE, zorder=3)
    axes[1].scatter([UTILIZATION], [base["per_token"] * 1e6], s=46, color=ORANGE, zorder=3)
    axes[0].legend(loc="upper right")
    fig.suptitle("Board-level TCO sensitivity: utilization and electricity price", fontsize=12)
    fig.text(0.5, 0.01, "Scope: accelerator board only. Excludes facility PUE, cooling, "
             "networking, storage and field failures.", ha="center", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(OUT_DIR / "tco_sensitivity.png", dpi=160)
    plt.close(fig)


def main():
    base = tco_metrics()
    print_tables(base)
    plot_sensitivity()
    print("\nSaved: tco_sensitivity.png (script directory)")


if __name__ == "__main__":
    main()
