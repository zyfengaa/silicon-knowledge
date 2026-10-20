#!/usr/bin/env python3
"""
文件名：power_model.py
描述：   CMOS 功耗与能效模型：动态功耗 P_dyn = alpha*C*V^2*f、静态漏电、
        DVFS 的 V-f 关系，以及每次操作能量与能量-延迟积（EDP）。
运行：   python power_model.py
输出：   终端打印不同 V/f 组合的功耗与 EDP 表、漏电-温度表；
        生成 power_model.png（与脚本同目录）。
参考：   Weste & Harris, CMOS VLSI Design, 4th ed., 2010, Ch. 5;
        Rabaey et al., Digital Integrated Circuits, 2nd ed., 2003, Ch. 5.
"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_DIR = Path(__file__).parent

# ---- 示例参数（工程估算，不是某产品的实测或签核数据）----
VDD_REF = 1.0            # 参考电压 (V)
VTH = 0.30               # 阈值电压 (V)
ALPHA_P = 1.5            # alpha-power law 指数
F_REF = 2.0e9            # 1.0 V 时的频率 (Hz)
C_TOTAL = 10e-9          # 总开关电容 (F)
ALPHA_ACT = 0.2          # 活动因子
I_LEAK_REF = 0.05        # 1.0 V、25 C 时的漏电 (A)
T_REF_C = 25.0
T_HOT_C = 100.0
LEAK_PER_10C = 1.5       # 温度每升 10 C 漏电倍数
P_STATES = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]


def freq_at_v(v):
    """alpha-power law 的 V-f 关系：f ~ ((V-Vth)^alpha)/V，并在 Vref 归一。"""
    v = np.asarray(v, dtype=float)
    vov = np.maximum(v - VTH, 1e-6)
    f = F_REF * (vov / (VDD_REF - VTH)) ** ALPHA_P * (VDD_REF / np.maximum(v, 1e-6))
    return np.where(v > VTH, f, 0.0)


def leak_current(v, temp_c):
    """简化漏电模型：随 V 线性、随温度每 10 C 乘固定倍数。"""
    return I_LEAK_REF * (v / VDD_REF) * LEAK_PER_10C ** ((temp_c - T_REF_C) / 10.0)


def power_arrays(v, temp_c=25.0):
    """返回 (频率, 动态功耗, 漏电功耗)，支持标量与数组。"""
    v = np.asarray(v, dtype=float)
    f = freq_at_v(v)
    p_dyn = ALPHA_ACT * C_TOTAL * v**2 * f
    p_leak = v * leak_current(v, temp_c)
    return f, p_dyn, p_leak


def main():
    print("CMOS 功耗模型（示例假设：C=10 nF, alpha=0.2, f_ref=2 GHz @ 1.0 V）")
    print("  V (V)  f (GHz)  P_dyn (W)  P_leak@25C (W)  P_total (W)  "
          "E_op (nJ)  EDP (rel.)")
    ref_edp = None
    for v in P_STATES:
        f, p_dyn, p_leak = (float(x) for x in power_arrays(v))
        p_total = p_dyn + p_leak
        e_op, edp = p_total / f, p_total / f**2
        ref_edp = edp if ref_edp is None else ref_edp
        print(f"  {v:5.2f}  {f / 1e9:7.2f}  {p_dyn:9.2f}  {p_leak:14.3f}  "
              f"{p_total:10.2f}  {e_op * 1e9:9.2f}  {edp / ref_edp:9.3f}")

    v_scan = np.linspace(0.4, 1.05, 201)
    f_scan, p_dyn_scan, p_leak_scan = power_arrays(v_scan)
    p_tot_scan = p_dyn_scan + p_leak_scan
    edp_scan = p_tot_scan / np.maximum(f_scan, 1e-9) ** 2
    i_opt = int(np.argmin(edp_scan))
    v_opt = float(v_scan[i_opt])
    print(f"\n  全扫描 EDP 最优点: V={v_opt:.2f} V, f={f_scan[i_opt] / 1e9:.2f} GHz, "
          f"P_total={p_tot_scan[i_opt]:.2f} W, "
          f"EDP={edp_scan[i_opt] / ref_edp:.3f}x (相对 1.0 V)")

    print("\n  静态漏电随温度（VDD = 1.0 V）")
    print("  T (C)  I_leak (mA)  P_leak (W)")
    for t in [25, 50, 75, 100]:
        i_leak = float(leak_current(VDD_REF, t))
        print(f"  {t:5.0f}  {i_leak * 1e3:11.2f}  {i_leak * VDD_REF:9.3f}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.8))
    _, _, p_leak_hot = power_arrays(v_scan, T_HOT_C)
    ax1.plot(v_scan, p_dyn_scan, label="Dynamic")
    ax1.plot(v_scan, p_leak_scan, label="Leakage @25C")
    ax1.plot(v_scan, p_tot_scan, label="Total @25C")
    ax1.plot(v_scan, p_dyn_scan + p_leak_hot, "--", label="Total @100C")
    ax1.set(xlabel="VDD (V)", ylabel="Power (W)",
            title="(a) Power and frequency vs VDD")
    ax1.grid(alpha=0.3)
    ax1.legend(fontsize=8)
    ax1b = ax1.twinx()
    ax1b.plot(v_scan, f_scan / 1e9, ":", color="gray", label="Frequency")
    ax1b.set_ylabel("Frequency (GHz)")
    ax1b.legend(fontsize=8, loc="center right")

    ax2.plot(v_scan, edp_scan / ref_edp, label="EDP / EDP(1.0 V)")
    ax2.plot(v_opt, edp_scan[i_opt] / ref_edp, "o", color="C3")
    ax2.annotate(f"min EDP @ {v_opt:.2f} V",
                 (v_opt, edp_scan[i_opt] / ref_edp),
                 xytext=(v_opt + 0.12, edp_scan[i_opt] / ref_edp + 0.1),
                 arrowprops=dict(arrowstyle="->", color="C3"), color="C3")
    ax2.set(xlabel="VDD (V)", ylabel="Normalized EDP",
            title="(b) Energy-delay product vs VDD")
    ax2.grid(alpha=0.3)
    ax2.legend(fontsize=9)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "power_model.png", dpi=150)
    plt.close(fig)
    print(f"  图已保存: {OUT_DIR / 'power_model.png'}")


if __name__ == "__main__":
    main()
