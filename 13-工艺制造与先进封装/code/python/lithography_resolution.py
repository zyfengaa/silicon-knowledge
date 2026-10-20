"""
文件名： lithography_resolution.py
描述：   用 Rayleigh 判据 R = k1·λ/NA、DOF = k2·λ/NA² 估算 193i、
        标准 EUV（NA=0.33）与 High-NA EUV（NA=0.55）的分辨率和焦深，
        并绘制 NA 扫描曲线，说明“提高 NA 换分辨率、牺牲焦深”的权衡。
运行：   python lithography_resolution.py
输出：   终端打印系统对比表和相对倍率；生成 lithography_resolution.png。
参考：   Levinson, Principles of Lithography, 4th ed., SPIE, 2019；
        Mack, Fundamental Principles of Optical Lithography, Wiley, 2007；
        IRDS Lithography 2023；ASML EXE/NXE 公开规格；SPECS.md §7.2。
"""

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ==================== 参数（集中在此处修改） ====================
K1 = 0.33                    # 分辨率工艺因子，量产常用 0.25–0.33
K2 = 0.50                    # 焦深工艺因子，公式量级估算
SYSTEMS = (                  # (名称, 真空波长 nm, 数值孔径)
    ("193i", 193.0, 1.35),
    ("EUV 0.33", 13.5, 0.33),
    ("High-NA", 13.5, 0.55),
)
NA_MIN, NA_MAX, NA_POINTS = 0.20, 1.35, 240
SURFACE, INK, SECONDARY = "#fcfcfb", "#0b0b0b", "#52514e"
MUTED, GRID = "#898781", "#e1e0d9"
BLUE, ORANGE = "#2a78d6", "#eb6834"
OUTPUT_PNG = Path(__file__).resolve().parent / "lithography_resolution.png"


def resolution(wavelength_nm: float, na: float) -> float:
    """Rayleigh 可分辨半周期，单位 nm。"""
    return K1 * wavelength_nm / na


def depth_of_focus(wavelength_nm: float, na: float) -> float:
    """Rayleigh 焦深，单位 nm。"""
    return K2 * wavelength_nm / na**2


def main() -> None:
    print("Rayleigh 光刻极限：R = k1*lambda/NA, DOF = k2*lambda/NA^2")
    print(f"参数：k1 = {K1:.2f}, k2 = {K2:.2f}\n")

    rows = []
    for name, wavelength, na in SYSTEMS:
        res = resolution(wavelength, na)
        dof = depth_of_focus(wavelength, na)
        rows.append((name, wavelength, na, res, dof))

    print(f"{'系统':<12}{'λ/nm':>8}{'NA':>7}{'R/nm':>10}{'DOF/nm':>10}"
          f"{'R/R_193i':>11}{'DOF/DOF_193i':>14}")
    print("-" * 72)
    ref_res, ref_dof = rows[0][3], rows[0][4]
    for name, wavelength, na, res, dof in rows:
        print(f"{name:<12}{wavelength:>8.1f}{na:>7.2f}{res:>10.1f}"
              f"{dof:>10.1f}{res / ref_res:>11.2f}{dof / ref_dof:>14.2f}")

    print("\n说明：193i 使用真空波长 193 nm 与浸没 NA=1.35；")
    print("      DOF 随 NA² 缩小，High-NA 的焦深仅为 EUV 0.33 的约"
          f" {rows[2][4] / rows[1][4]:.2f} 倍。")
    print("      表中数值为公式量级估算，不代表设备保证规格。")

    # -------- 绘图：两个子图共享 NA 横轴，避免双纵轴 --------
    na_axis = np.linspace(NA_MIN, NA_MAX, NA_POINTS)
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.8),
                             constrained_layout=True)
    fig.patch.set_facecolor(SURFACE)
    fig.suptitle("Rayleigh lithography limits", color=INK,
                 fontsize=14, fontweight="bold", x=0.02, ha="left")

    curves = ((193.0, "193 nm", BLUE), (13.5, "13.5 nm", ORANGE))
    for ax, metric, ylabel, title in (
        (axes[0], resolution, "Resolution half-pitch R (nm)", "Resolution vs NA"),
        (axes[1], depth_of_focus, "Depth of focus DOF (nm)", "DOF vs NA"),
    ):
        for wavelength, label, color in curves:
            ax.semilogy(na_axis, metric(wavelength, na_axis),
                        color=color, lw=2, label=label)
        ax.set_facecolor(SURFACE)
        ax.set_xlabel("Numerical aperture NA", color=SECONDARY)
        ax.set_ylabel(ylabel, color=SECONDARY)
        ax.set_title(title, loc="left", color=INK, fontsize=11)
        ax.set_xlim(NA_MIN, NA_MAX + 0.04)
        ax.grid(True, which="major", color=GRID, lw=0.8)
        ax.grid(True, which="minor", color=GRID, lw=0.4, alpha=0.55)
        ax.tick_params(colors=MUTED, labelsize=9)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#c3c2b7")
        ax.legend(frameon=False, labelcolor=INK, loc="upper right")

    res_offsets = {"193i": (-42, 9), "EUV 0.33": (7, 9), "High-NA": (8, 8)}
    dof_offsets = {"193i": (-46, 9), "EUV 0.33": (7, 9), "High-NA": (7, -15)}
    for name, wavelength, na, res, dof in rows:
        color = BLUE if wavelength == 193.0 else ORANGE
        for ax, value, offsets in ((axes[0], res, res_offsets),
                                   (axes[1], dof, dof_offsets)):
            ax.plot(na, value, "o", ms=8, mfc=color, mec=SURFACE,
                    mew=2, linestyle="none", zorder=5)
            ax.annotate(name, (na, value), xytext=offsets[name],
                        textcoords="offset points", color=SECONDARY,
                        fontsize=8.5, ha="left")

    fig.savefig(OUTPUT_PNG, dpi=160, facecolor=SURFACE,
                bbox_inches="tight")
    plt.close(fig)
    print(f"\n已生成图像：{OUTPUT_PNG}")


if __name__ == "__main__":
    main()
