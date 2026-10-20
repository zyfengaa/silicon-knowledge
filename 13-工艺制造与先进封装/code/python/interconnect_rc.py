"""
文件名： interconnect_rc.py
描述：   用 R = ρL/(w·t) 与“面积电容 + 侧壁边缘电容”的简化模型估计
        Cu 互连的 RC 延迟；比较线宽、长度和低-k 介质的影响（线宽扫描
        时间距按 1:1 随线宽缩放），并演示每 1 mm 插入中继器后延迟
        从 ∝L² 转为近似 ∝L 的趋势。
运行：   python interconnect_rc.py
输出：   终端打印几何/材料参数表、线宽与介质对比表、长度与中继器表；
        生成 interconnect_rc.png。
参考：   Weste & Harris, CMOS VLSI Design, 4th ed., 2010, Ch.4–5；
        Bohr, “Interconnect Scaling—The Real Limiter,” IEDM 1995；
        IRDS Interconnect 2023；本仓库 13-04-beol.md；SPECS.md §8.1。
"""

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ==================== 参数（集中在此处修改） ====================
EPS0 = 8.854_187_812e-12      # 真空介电常数，F/m
RHO_CU = 1.68e-8             # 体铜电阻率，Ω·m（未含尺寸效应）
WIDTHS_NM = np.array([16.0, 24.0, 32.0, 48.0, 64.0])
THICKNESS_NM = 70.0          # 线厚 t
ILD_NM = 70.0                # 上下介质等效厚度 h（面积电容）
SPACING_TO_WIDTH = 1.0       # 线间距 s = 1.0·w（宽度扫描时同比缩放）
DIELECTRICS = (("SiO2", 3.9), ("SiOC", 2.7), ("ULK", 2.3))
REF_WIDTH_NM, REF_K = 32.0, 2.7
TABLE_LENGTH_MM = 1.0        # 对比表使用的线长
REPEATER_SPACING_MM = 1.0    # 中继器插入间距
REPEATER_DELAY_PS = 20.0     # 每个中继器自身延迟
LENGTHS_MM = np.logspace(-1, 2, 300)
SURFACE, INK, SECONDARY = "#fcfcfb", "#0b0b0b", "#52514e"
MUTED, GRID = "#898781", "#e1e0d9"
BLUE, ORANGE = "#2a78d6", "#eb6834"
OUTPUT_PNG = Path(__file__).resolve().parent / "interconnect_rc.png"


def rc_metrics(width_nm: float, length_mm: float, k_dielectric: float,
               use_repeaters: bool = False) -> tuple[float, float, float, int]:
    """返回 (R/Ω, C/F, 分布 RC 延迟/ps, 分段数)。

    面积项：C_area = ε0·k·w·L/h
    边缘项：C_fringe = 2·ε0·k·t·L/s（两侧壁平行板近似）
    分布线的 Elmore 延迟取 R·C/2；插入中继器后每段重新按 R/k·C/k 计。
    """
    width, length = width_nm * 1e-9, length_mm * 1e-3
    thickness, height = THICKNESS_NM * 1e-9, ILD_NM * 1e-9
    spacing = SPACING_TO_WIDTH * width
    if spacing <= 0:
        raise ValueError("线间距必须为正")

    resistance = RHO_CU * length / (width * thickness)
    cap_area = EPS0 * k_dielectric * width * length / height
    cap_fringe = 2.0 * EPS0 * k_dielectric * thickness * length / spacing
    capacitance = cap_area + cap_fringe
    delay_ps = 0.5 * resistance * capacitance * 1e12

    segments = 1
    if use_repeaters:
        segments = max(1, int(np.ceil(length_mm / REPEATER_SPACING_MM)))
        delay_ps = delay_ps / segments + (segments - 1) * REPEATER_DELAY_PS
    return resistance, capacitance, delay_ps, segments


def main() -> None:
    print("互连 RC 模型：R = rho*L/(w*t)，C = C_area + C_fringe")
    print(f"Cu rho = {RHO_CU * 1e8:.2f} uOhm*cm；t = {THICKNESS_NM:.0f} nm，"
          f"h = {ILD_NM:.0f} nm，s = {SPACING_TO_WIDTH:.1f}*w")
    print(f"中继器：每 {REPEATER_SPACING_MM:.1f} mm 一个，"
          f"每个 {REPEATER_DELAY_PS:.0f} ps\n")

    print(f"[1] 线宽扫描（s = {SPACING_TO_WIDTH:.1f}w）  "
          f"L = {TABLE_LENGTH_MM:.1f} mm, SiOC k = {REF_K:.1f}")
    print(f"{'w/nm':>6}{'s/nm':>7}{'R/kOhm':>10}{'C/fF':>9}"
          f"{'RC delay/ps':>14}")
    print("-" * 46)
    for width in WIDTHS_NM:
        resistance, capacitance, delay_ps, _ = rc_metrics(
            width, TABLE_LENGTH_MM, REF_K)
        spacing = SPACING_TO_WIDTH * width
        print(f"{width:>6.0f}{spacing:>7.0f}{resistance / 1e3:>10.2f}"
              f"{capacitance * 1e15:>9.1f}{delay_ps:>14.1f}")
    print("\n注：更宽的线同时降低 R 并放宽边缘电容间距，因此 RC 明显下降。")

    print(f"\n[2] 介质扫描  w = {REF_WIDTH_NM:.0f} nm, L = {TABLE_LENGTH_MM:.1f} mm")
    print(f"{'介质':<10}{'k':>6}{'C/fF':>10}{'RC delay/ps':>14}")
    print("-" * 40)
    for name, k_dielectric in DIELECTRICS:
        _, capacitance, delay_ps, _ = rc_metrics(
            REF_WIDTH_NM, TABLE_LENGTH_MM, k_dielectric)
        print(f"{name:<10}{k_dielectric:>6.1f}{capacitance * 1e15:>10.1f}"
              f"{delay_ps:>14.1f}")

    print(f"\n[3] 长度与中继器  w = {REF_WIDTH_NM:.0f} nm, k = {REF_K:.1f}")
    print(f"{'L/mm':>7}{'直接/ps':>15}{'中继器/ps':>16}"
          f"{'段数':>7}{'加速比':>9}")
    print("-" * 54)
    for length_mm in (0.1, 1.0, 10.0, 100.0):
        _, _, direct_ps, _ = rc_metrics(REF_WIDTH_NM, length_mm, REF_K)
        _, _, repeated_ps, segments = rc_metrics(
            REF_WIDTH_NM, length_mm, REF_K, use_repeaters=True)
        print(f"{length_mm:>7.1f}{direct_ps:>15,.1f}"
              f"{repeated_ps:>16,.1f}{segments:>7d}"
              f"{direct_ps / repeated_ps:>9.1f}x")

    direct = np.array([rc_metrics(REF_WIDTH_NM, length, REF_K)[2]
                       for length in LENGTHS_MM])
    repeated = np.array([rc_metrics(REF_WIDTH_NM, length, REF_K, True)[2]
                         for length in LENGTHS_MM])

    fig, ax = plt.subplots(figsize=(9.2, 5.2), constrained_layout=True)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.loglog(LENGTHS_MM, direct / 1e3, color=BLUE, lw=2,
              label="Direct line: RC ∝ L²")
    ax.loglog(LENGTHS_MM, repeated / 1e3, color=ORANGE, lw=2,
              label=f"Repeater every {REPEATER_SPACING_MM:.0f} mm: ≈ L")
    ax.set_xlabel("Interconnect length L (mm)", color=SECONDARY)
    ax.set_ylabel("Elmore RC delay (ns)", color=SECONDARY)
    ax.set_title("Cu interconnect RC delay vs length", loc="left",
                 color=INK, fontsize=13, fontweight="bold", pad=26)
    ax.text(0.0, 1.01, f"w = {REF_WIDTH_NM:.0f} nm, t = {THICKNESS_NM:.0f} nm, "
            f"k = {REF_K:.1f}; repeater delay = {REPEATER_DELAY_PS:.0f} ps",
            transform=ax.transAxes, color=MUTED, fontsize=9, va="bottom")
    ax.grid(True, which="major", color=GRID, lw=0.8)
    ax.grid(True, which="minor", color=GRID, lw=0.4, alpha=0.55)
    ax.tick_params(colors=MUTED, labelsize=9)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.legend(frameon=False, labelcolor=INK, loc="upper left")
    ax.annotate(f"{direct[-1] / 1e3:.0f} ns", (LENGTHS_MM[-1], direct[-1] / 1e3),
                xytext=(-8, 8), textcoords="offset points", ha="right",
                color=SECONDARY, fontsize=9)
    ax.annotate(f"{repeated[-1] / 1e3:.0f} ns", (LENGTHS_MM[-1], repeated[-1] / 1e3),
                xytext=(-8, 8), textcoords="offset points", ha="right",
                color=SECONDARY, fontsize=9)

    fig.savefig(OUTPUT_PNG, dpi=160, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"\n已生成图像：{OUTPUT_PNG}")


if __name__ == "__main__":
    main()
