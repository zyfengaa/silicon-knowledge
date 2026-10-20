#!/usr/bin/env python3
"""
文件名：  yield_sim.py
描述：    Poisson、Murphy 与负二项三种良率模型的对比，并给出缺陷团簇的蒙特卡洛示例。
         绘制良率随 die 面积变化的曲线，以及一张 300 mm 晶圆上的成团缺陷与好/坏 die 图。
运行：   python yield_sim.py
输出：   yield_vs_area.png、defect_cluster_map.png，终端打印模型对比表与蒙特卡洛结果。
参考：   [1] SPECS.md §8.2（Poisson / Murphy / 负二项公式）
         [2] Murphy, B. T. "Cost-Size Optima of Monolithic Integrated Circuits." Proc. IEEE, 1964.
         [3] Stapper, C. H. "Defect Density Distribution for LSI Yield Calculations." IEEE TED, 1973.
注意：   所有参数均为示例假设，不构成采购、报价或验收依据。
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Patch
from matplotlib.ticker import PercentFormatter
# --------------------------- 参数（示例假设） ---------------------------
OUT_DIR = Path(__file__).resolve().parent
SEED = 42
D0_LIST = (0.1, 0.5, 1.0)            # defects/cm²
AREA_MM2 = np.linspace(25.0, 900.0, 300)
ALPHA_CLUSTER = 2.0                  # 负二项团簇参数（工程拟合值）
WAFER_RADIUS_MM, EDGE_EXCLUSION_MM = 150.0, 3.0
DIE_SIDE_MM = 12.0                   # 12 × 12 mm = 1.44 cm²
D0_MC, CLUSTER_FRACTION = 0.3, 0.8   # 平均缺陷密度 / 成团缺陷占比
N_CLUSTERS, CLUSTER_SIGMA_MM = 12, 8.0
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb"
GOOD_FILL, BAD_FILL = "#1baf7a", "#e34948"
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                     "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10, "legend.frameon": False, "lines.linewidth": 2.0})

# ------------------------------- 良率模型 -------------------------------
def yield_poisson(area_cm2, d0):  # 泊松：Y = exp(-A·D0)
    return np.exp(-np.asarray(area_cm2) * d0)

def yield_murphy(area_cm2, d0):  # Murphy：Y = ((1-e^-x)/x)²，x = A·D0
    x = np.asarray(area_cm2, dtype=float) * d0
    safe_x = np.where(x < 1e-9, 1.0, x)
    return np.where(x < 1e-9, 1.0, ((1.0 - np.exp(-safe_x)) / safe_x) ** 2)

def yield_negative_binomial(area_cm2, d0, alpha=ALPHA_CLUSTER):  # Y = (1+A·D0/α)^(-α)
    return (1.0 + np.asarray(area_cm2) * d0 / alpha) ** (-alpha)

def simulate_clustered_wafer(rng):
    """在 300 mm 晶圆上撒缺陷（80% 成团、20% 随机），按 12 mm die 统计良率。"""
    wafer_area = np.pi * (WAFER_RADIUS_MM / 10.0) ** 2
    n_total = int(round(D0_MC * wafer_area))
    n_clustered = int(round(n_total * CLUSTER_FRACTION))
    n_random = n_total - n_clustered
    # 团簇：随机中心 + 高斯扰动；随机背景：圆盘内均匀采样
    theta = rng.uniform(0.0, 2.0 * np.pi, N_CLUSTERS)
    radius = 0.92 * WAFER_RADIUS_MM * np.sqrt(rng.uniform(size=N_CLUSTERS))
    centers = np.column_stack([radius * np.cos(theta), radius * np.sin(theta)])
    clustered = centers[rng.integers(0, N_CLUSTERS, n_clustered)] + rng.normal(
        0.0, CLUSTER_SIGMA_MM, size=(n_clustered, 2))
    clustered = clustered[np.hypot(clustered[:, 0], clustered[:, 1]) <= WAFER_RADIUS_MM]
    theta = rng.uniform(0.0, 2.0 * np.pi, n_random)
    radius = WAFER_RADIUS_MM * np.sqrt(rng.uniform(size=n_random))
    random_pts = np.column_stack([radius * np.cos(theta), radius * np.sin(theta)])
    # 把缺陷映射到 die 网格
    grid_half = DIE_SIDE_MM * np.floor(WAFER_RADIUS_MM / DIE_SIDE_MM)
    n_side = int(2 * grid_half / DIE_SIDE_MM) + 1
    x0 = -grid_half - DIE_SIDE_MM / 2.0
    counts = np.zeros((n_side, n_side), dtype=int)
    for pts in (clustered, random_pts):
        ix = np.floor((pts[:, 0] - x0) / DIE_SIDE_MM).astype(int)
        iy = np.floor((pts[:, 1] - x0) / DIE_SIDE_MM).astype(int)
        valid = (ix >= 0) & (ix < n_side) & (iy >= 0) & (iy < n_side)
        np.add.at(counts, (ix[valid], iy[valid]), 1)
    c = x0 + (np.arange(n_side) + 0.5) * DIE_SIDE_MM
    xx, yy = np.meshgrid(c, c, indexing="ij")
    usable = np.hypot(xx, yy) <= WAFER_RADIUS_MM - EDGE_EXCLUSION_MM - DIE_SIDE_MM / 2
    good = (counts == 0) & usable
    return {"usable": usable, "good": good, "xx": xx, "yy": yy,
            "clustered": clustered, "random": random_pts, "n_dies": int(usable.sum()),
            "yield": good.sum() / usable.sum(), "area_cm2": (DIE_SIDE_MM / 10.0) ** 2,
            "d0_eff": (len(clustered) + len(random_pts)) / wafer_area}

# ------------------------------- 绘图 -------------------------------
def plot_yield_curves():  # 三联图：每个 D0 一张，比较三种模型
    area_cm2 = AREA_MM2 / 100.0
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.0), sharey=True)
    for ax, d0 in zip(axes, D0_LIST):
        ax.plot(area_cm2, yield_poisson(area_cm2, d0), color=BLUE, label="Poisson")
        ax.plot(area_cm2, yield_murphy(area_cm2, d0), color=ORANGE, label="Murphy")
        ax.plot(area_cm2, yield_negative_binomial(area_cm2, d0), color=AQUA,
                label=f"Negative binomial (α={ALPHA_CLUSTER:g})")
        ax.set(title=f"D0 = {d0:.1f} defects/cm²", xlabel="Die area (cm²)",
               xlim=(0, area_cm2[-1]), ylim=(0, 1.02))
        ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    axes[0].set_ylabel("Wafer-sort yield")
    axes[0].legend(loc="upper right", fontsize=9)
    fig.suptitle("Yield vs die area: model comparison (example assumptions)", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "yield_vs_area.png", dpi=160)
    plt.close(fig)

def plot_wafer_map(mc):  # 晶圆图：坏 die 红、好 die 绿，叠加两类缺陷
    fig, ax = plt.subplots(figsize=(7.4, 7.4))
    fill = np.where(mc["good"], GOOD_FILL, BAD_FILL)
    ax.scatter(mc["xx"][mc["usable"]], mc["yy"][mc["usable"]], marker="s", s=380,
               c=fill[mc["usable"]], alpha=0.22, edgecolors=SURFACE, linewidths=0.4)
    ax.scatter(mc["clustered"][:, 0], mc["clustered"][:, 1], s=6, color=BLUE,
               alpha=0.55, linewidths=0, label=f"Clustered defects ({len(mc['clustered'])})")
    ax.scatter(mc["random"][:, 0], mc["random"][:, 1], s=6, color=ORANGE,
               alpha=0.75, linewidths=0, label=f"Random defects ({len(mc['random'])})")
    ax.add_patch(Circle((0, 0), WAFER_RADIUS_MM, fill=False, color=MUTED, linewidth=1.0))
    handles = [Patch(facecolor=GOOD_FILL, alpha=0.30, label=f"Good die ({mc['good'].sum()})"),
               Patch(facecolor=BAD_FILL, alpha=0.30,
                     label=f"Bad die ({(mc['usable'] & ~mc['good']).sum()})")]
    ax.legend(handles=handles + ax.get_legend_handles_labels()[0], loc="upper right", fontsize=8)
    ax.text(-148, -142, f"300 mm wafer · {DIE_SIDE_MM:g} mm die\n"
            f"Effective D0 = {mc['d0_eff']:.3f} defects/cm²\n"
            f"Monte Carlo yield = {mc['yield']:.1%}", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.4", facecolor=SURFACE, edgecolor=GRID))
    ax.set(xlim=(-156, 156), ylim=(-156, 156), aspect="equal")
    ax.set_axis_off()
    ax.set_title("Clustered defects raise the clean-die fraction", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "defect_cluster_map.png", dpi=160)
    plt.close(fig)

def print_tables(mc):  # 打印模型对比与蒙特卡洛结果
    print("Yield model comparison (example assumptions)")
    print(f"{'D0':>6s} {'A(mm2)':>8s} {'A(cm2)':>7s} {'Poisson':>9s} "
          f"{'Murphy':>8s} {'NegBin':>8s}")
    print("-" * 52)
    for d0 in D0_LIST:
        for area_mm2 in (100.0, 400.0, 800.0):
            a = area_mm2 / 100.0
            print(f"{d0:6.1f} {area_mm2:8.0f} {a:7.2f} "
                  f"{float(yield_poisson(a, d0)):9.1%} {float(yield_murphy(a, d0)):8.1%} "
                  f"{float(yield_negative_binomial(a, d0)):8.1%}")
        print("-" * 52)
    a, d0 = mc["area_cm2"], mc["d0_eff"]
    print(f"\nMonte Carlo clustered-defect example (example assumptions)\n"
          f"  Dies on wafer: {mc['n_dies']}, die area: {a:.2f} cm2, "
          f"effective D0: {d0:.3f} defects/cm2")
    print(f"  Monte Carlo yield : {mc['yield']:.1%}")
    for name, func in (("Poisson", yield_poisson), ("Murphy", yield_murphy),
                       ("Negative binomial", yield_negative_binomial)):
        print(f"  {name:<18s}: {float(func(a, d0)):.1%}")
    print("  Clustering leaves more die completely defect-free than Poisson assumes.")

def main():
    mc = simulate_clustered_wafer(np.random.default_rng(SEED))
    plot_yield_curves()
    plot_wafer_map(mc)
    print_tables(mc)
    print("\nSaved: yield_vs_area.png, defect_cluster_map.png (script directory)")

if __name__ == "__main__":
    main()
