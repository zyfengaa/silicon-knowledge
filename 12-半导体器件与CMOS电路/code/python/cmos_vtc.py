#!/usr/bin/env python3
"""
文件名：cmos_vtc.py
描述：   用简化平方律 nMOS/pMOS 电流模型求解 CMOS 反相器电压传输特性（VTC），
        标注 VOH/VOL/VM/VIL/VIH 并计算噪声容限；扫描 beta ratio 观察 VM 移动。
运行：   python cmos_vtc.py
输出：   终端打印各 beta ratio 的 VM、NMH、NML；
        生成 cmos_vtc.png（与脚本同目录）。
参考：   Rabaey et al., Digital Integrated Circuits, 2nd ed., 2003, Ch. 5;
        Weste & Harris, CMOS VLSI Design, 4th ed., 2010, Ch. 1.
"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_DIR = Path(__file__).parent

# ---- 示例参数（量级参考 SPECS §7.1，不是 PDK 数值）----
VDD = 1.0
VTN = 0.30
VTP_ABS = 0.30
BETA_N = 200e-6          # uA/V^2
BETA_P = 100e-6          # 基准 beta_n/beta_p = 2
LAMBDA = 0.05            # 1/V
BETA_RATIOS = [0.5, 1.0, 1.5, 2.0, 3.0]
BASE_RATIO = 2.0
N_POINTS = 401


def mos_current(vgs, vds, beta, vth):
    """nMOS/pMOS 共用的平方律电流；pMOS 传入 |Vgs|、|Vds|、|Vth|。"""
    if vgs <= vth or vds <= 0.0:
        return 0.0
    vov = vgs - vth
    if vds < vov:
        return beta * (vov * vds - 0.5 * vds**2) * (1.0 + LAMBDA * vds)
    return 0.5 * beta * vov**2 * (1.0 + LAMBDA * vds)


def solve_vout(vin, beta_p):
    """在 [0, VDD] 内二分求解 In(Vin,Vout) = Ip(Vin,Vout)。"""
    def imbalance(vout):
        i_n = mos_current(vin, vout, BETA_N, VTN)
        i_p = mos_current(VDD - vin, VDD - vout, beta_p, VTP_ABS)
        return i_n - i_p

    lo, hi = 0.0, VDD
    if imbalance(hi) <= 0.0:
        return VDD
    if imbalance(lo) >= 0.0:
        return 0.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if imbalance(mid) > 0.0:   # In 偏强，向低 Vout 收缩
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def vtc(beta_p):
    vin = np.linspace(0.0, VDD, N_POINTS)
    vout = np.array([solve_vout(float(v), beta_p) for v in vin])
    return vin, vout


def cross_at(vin, slope, level, idx):
    """在 idx-1、idx 之间线性插值出斜率等于 level 的输入电压。"""
    j = max(idx - 1, 0)
    y0, y1 = slope[j], slope[idx]
    if y0 == y1:
        return float(vin[idx])
    return float(vin[j] + (level - y0) * (vin[idx] - vin[j]) / (y1 - y0))


def metrics(vin, vout):
    """提取 VOH/VOL/VM/VIL/VIH 与噪声容限。"""
    voh, vol = float(vout[0]), float(vout[-1])
    vm = float(vin[int(np.argmin(np.abs(vout - vin)))])
    slope = np.gradient(vout, vin)
    i_vil = int(np.argmax(slope <= -1.0))
    i_vih = int(np.argmax((vin > vm) & (slope >= -1.0)))
    vil = cross_at(vin, slope, -1.0, i_vil)
    vih = cross_at(vin, slope, -1.0, i_vih)
    return dict(voh=voh, vol=vol, vm=vm, vil=vil, vih=vih,
                nmh=voh - vih, nml=vil - vol)


def main():
    fig, ax = plt.subplots(figsize=(7.2, 6.2))
    ax.plot([0, VDD], [0, VDD], color="gray", ls=":", lw=1,
            label="Vin = Vout")
    base = None

    print("CMOS 反相器 VTC（平方律模型，示例参数）")
    print(f"  VDD={VDD:.2f} V, Vthn={VTN:.2f} V, |Vthp|={VTP_ABS:.2f} V, "
          f"beta_n={BETA_N * 1e6:.0f} uA/V^2")
    print("  beta_n/beta_p     VM (V)   NMH (V)   NML (V)")
    for ratio in BETA_RATIOS:
        vin, vout = vtc(BETA_N / ratio)
        m = metrics(vin, vout)
        if abs(ratio - BASE_RATIO) < 1e-9:
            base = m
            ax.plot(vin, vout, lw=2.6, color="C3",
                    label=f"beta ratio = {ratio:.1f} (base)")
            ax.plot(m["vm"], m["vm"], "o", color="C3", ms=7)
            ax.axhline(m["voh"], color="C0", ls="--", lw=1, alpha=0.7)
            ax.axhline(m["vol"], color="C0", ls="--", lw=1, alpha=0.7)
            ax.axvline(m["vil"], color="C2", ls="--", lw=1, alpha=0.7)
            ax.axvline(m["vih"], color="C2", ls="--", lw=1, alpha=0.7)
        else:
            ax.plot(vin, vout, lw=1.2, alpha=0.75,
                    label=f"beta ratio = {ratio:.1f}")
        print(f"  {ratio:8.1f}      {m['vm']:7.3f}   {m['nmh']:7.3f}   "
              f"{m['nml']:7.3f}")

    m = base
    ax.annotate(f"VM = {m['vm']:.3f} V", (m["vm"], m["vm"]),
                xytext=(m["vm"] + 0.10, m["vm"] - 0.13),
                arrowprops=dict(arrowstyle="->", color="C3"), color="C3")
    ax.text(0.03, m["voh"] - 0.06, f"VOH = {m['voh']:.2f} V", color="C0")
    ax.text(0.03, m["vol"] + 0.03, f"VOL = {m['vol']:.2f} V", color="C0")
    ax.text(m["vil"] - 0.10, 0.03, f"VIL={m['vil']:.2f}", color="C2")
    ax.text(m["vih"] + 0.02, 0.03, f"VIH={m['vih']:.2f}", color="C2")

    k = np.sqrt(BETA_N / BETA_P)
    vm_analytic = (VDD + k * VTN - VTP_ABS) / (1.0 + k)
    print(f"\n  基准 beta ratio={BASE_RATIO:.1f}: VM(数值)={m['vm']:.3f} V, "
          f"VM(饱和区解析)={vm_analytic:.3f} V")
    print(f"  NMH = VOH - VIH = {m['nmh']:.3f} V; "
          f"NML = VIL - VOL = {m['nml']:.3f} V")
    print("  beta ratio 增大（nMOS 相对更强）时 VM 下移，反之 VM 上移。")

    ax.set(xlim=(0, VDD), ylim=(0, VDD), xlabel="Vin (V)", ylabel="Vout (V)",
           title=f"CMOS Inverter VTC (beta_n/beta_p scan, VDD={VDD:.1f} V)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "cmos_vtc.png", dpi=150)
    plt.close(fig)
    print(f"  图已保存: {OUT_DIR / 'cmos_vtc.png'}")


if __name__ == "__main__":
    main()
