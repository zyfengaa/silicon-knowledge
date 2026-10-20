#!/usr/bin/env python3
"""
文件名：mosfet_iv.py
描述：   长沟道 nMOS 的平方律 I-V 模型，绘制 Id-Vgs（线性与对数）和 Id-Vds
        曲线；并用速度饱和近似展示短沟道器件的简化对比。
运行：   python mosfet_iv.py
输出：   终端打印 Vth、亚阈值摆幅和关键工作点电流；
        生成 mosfet_iv.png（与脚本同目录）。
参考：   Sze & Ng, Physics of Semiconductor Devices, 3rd ed., 2007, Ch. 6;
        Weste & Harris, CMOS VLSI Design, 4th ed., 2010, Ch. 2.
"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_DIR = Path(__file__).parent

# ---- 器件参数（示例假设，口径参考 SPECS §7.1，不是 PDK 数值）----
VDD = 1.0                # 电源电压 (V)
VTN = 0.4                # 阈值电压 (V)
MU_N_COX = 300e-6        # mu_n * C_ox (A/V^2)
W_OVER_L = 2.0           # 宽长比
LAMBDA = 0.03            # 沟道长度调制系数 (1/V)
SUBTH_SWING = 0.080      # 亚阈值摆幅 (V/dec)
I_AT_VTH = 100e-9        # Vgs = Vth 时的亚阈值电流 (A)
V_T = 0.0259             # 300 K 热电压 (V)

# ---- 短沟道简化对比参数 ----
MU_N = 0.03              # 迁移率 (m^2/V/s)
COX = MU_N_COX / MU_N    # 栅电容密度 (F/m^2)
V_SAT = 1e5              # 饱和速度 (m/s)
W_SHORT = 2e-6           # 短沟道器件宽度 (m)


def square_law(vgs, vds):
    """长沟道平方律：线性区 + 饱和区，饱和区含沟道长度调制。"""
    vov = np.maximum(vgs - VTN, 0.0)
    triode = MU_N_COX * W_OVER_L * (vov * vds - 0.5 * vds**2)
    sat = 0.5 * MU_N_COX * W_OVER_L * vov**2 * (1.0 + LAMBDA * vds)
    return np.where(vds < vov, triode, sat)


def subthreshold(vgs, vds):
    """亚阈值指数电流；在 Vth 处封顶，便于与强反型模型衔接。"""
    i_sub = I_AT_VTH * 10.0 ** ((vgs - VTN) / SUBTH_SWING)
    i_sub *= 1.0 - np.exp(-vds / V_T)
    return np.minimum(i_sub, I_AT_VTH)


def drain_current(vgs, vds):
    """弱反型与强反型取较大者，得到完整的开关特性。"""
    return np.maximum(square_law(vgs, vds), subthreshold(vgs, vds))


def short_channel_current(vgs, vds):
    """速度饱和近似：Id,sat ~ W*v_sat*C_ox*Vov，用 tanh 平滑进入饱和。"""
    vov = max(vgs - VTN, 1e-6)
    i_sat = W_SHORT * V_SAT * COX * vov
    return i_sat * np.tanh(vds / vov)


def main():
    vgs = np.linspace(0.0, VDD, 501)
    vds = np.linspace(0.0, VDD, 401)
    vgs_list = [0.6, 0.8, 1.0]

    i_lin = drain_current(vgs, 0.05)
    i_sat = drain_current(vgs, VDD)
    i_off = float(drain_current(0.0, VDD))
    i_on = float(drain_current(VDD, VDD))

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.4))
    ax = axes[0]
    ax.plot(vgs, i_lin * 1e6, label="Vds = 0.05 V (linear)")
    ax.plot(vgs, i_sat * 1e6, label="Vds = 1.0 V (saturation)")
    ax.axvline(VTN, color="gray", ls=":", label="Vth")
    ax.set(xlabel="Vgs (V)", ylabel="Id (uA)", title="(a) Id-Vgs, linear scale")
    ax.grid(alpha=0.3)
    ax.legend()

    ax = axes[1]
    ax.semilogy(vgs, np.maximum(i_lin, 1e-15), label="Vds = 0.05 V")
    ax.semilogy(vgs, np.maximum(i_sat, 1e-15), label="Vds = 1.0 V")
    ax.axvline(VTN, color="gray", ls=":")
    ax.set(xlabel="Vgs (V)", ylabel="Id (A)", title="(b) Id-Vgs, log scale")
    ax.grid(alpha=0.3, which="both")
    ax.legend()

    ax = axes[2]
    for vg in vgs_list:
        ax.plot(vds, square_law(vg, vds) * 1e6, label=f"Vgs = {vg:.1f} V")
        ax.axvline(vg - VTN, color="gray", ls=":", alpha=0.4)
    ax.plot(vds, short_channel_current(1.0, vds) * 1e6, "k--",
            label="short-channel (Vgs=1.0 V)")
    ax.set(xlabel="Vds (V)", ylabel="Id (uA)", title="(c) Id-Vds output curves")
    ax.grid(alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(OUT_DIR / "mosfet_iv.png", dpi=150)
    plt.close(fig)

    print("长沟道 nMOS 平方律模型（示例假设，不是 PDK 数值）")
    print(f"  Vth = {VTN:.2f} V, VDD = {VDD:.2f} V, "
          f"beta = {MU_N_COX * W_OVER_L * 1e6:.0f} uA/V^2")
    print(f"  亚阈值摆幅 S = {SUBTH_SWING * 1e3:.0f} mV/dec; "
          f"Ioff(Vgs=0) = {i_off / 1e-12:.2f} pA")
    print(f"  每 100 mV 电流变化约 {10 ** (0.1 / SUBTH_SWING):.1f} 倍")
    print(f"  Ion(Vgs=Vds={VDD:.1f} V) = {i_on * 1e6:.1f} uA")
    print("  Vgs (V)   Id@Vds=0.05V (uA)   Id@Vds=1.0V (uA)")
    for vg in vgs_list:
        print(f"  {vg:5.1f}   {float(square_law(vg, 0.05)) * 1e6:14.1f}"
              f"   {float(square_law(vg, VDD)) * 1e6:14.1f}")
    i_sc = short_channel_current(1.0, VDD)
    print(f"  短沟道速度饱和近似: Vgs=1.0 V 时 Id,sat = {i_sc * 1e3:.2f} mA")
    print(f"  平方律的对比值: {float(square_law(1.0, VDD)) * 1e6:.1f} uA")
    print(f"  图已保存: {OUT_DIR / 'mosfet_iv.png'}")


if __name__ == "__main__":
    main()
