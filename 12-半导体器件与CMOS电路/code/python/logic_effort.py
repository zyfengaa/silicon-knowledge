#!/usr/bin/env python3
"""
文件名：logic_effort.py
描述：   用逻辑努力（g/h/p）模型计算给定组合路径的延迟、最优级数与 FO4 估算；
        扫描级数观察“每级努力约 4”的经验法则。
运行：   python logic_effort.py
输出：   终端打印门库、路径汇总、逐级延迟表与级数扫描表；
        生成 logic_effort.png（与脚本同目录）。
参考：   Sutherland, Sproull & Harris, Logical Effort, 1999, Ch. 1-3;
        Weste & Harris, CMOS VLSI Design, 4th ed., 2010, Ch. 4.
"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_DIR = Path(__file__).parent

# ---- 门库：(逻辑努力 g, 归一化寄生延迟 p) ----
GATES = {
    "INV": (1.0, 1.0),
    "NAND2": (4.0 / 3.0, 2.0),
    "NOR2": (5.0 / 3.0, 2.0),
    "NAND3": (5.0 / 3.0, 3.0),
    "NOR3": (7.0 / 3.0, 3.0),
    "XOR2": (2.0, 4.0),
}

# ---- 待分析路径：(门名, 分支努力 b) ----
PATH = [("NAND2", 1.0), ("NOR2", 1.0), ("INV", 1.0)]
H_PATH = 20.0            # 路径电气努力 Cout/Cin
FO4_DELAY_PS = 6.0       # 7nm 级示例，公开估算 5-8 ps
TAU_PS = FO4_DELAY_PS / 5.0
MAX_STAGES = 8


def path_metrics(path, h_path):
    """按等努力分配计算路径 G/B/H/F/P 与逐级 h、d。"""
    g = np.array([GATES[name][0] for name, _ in path])
    p = np.array([GATES[name][1] for name, _ in path])
    b = np.array([br for _, br in path])
    G, B, P = float(np.prod(g)), float(np.prod(b)), float(np.sum(p))
    F = G * B * h_path
    n = len(path)
    f = F ** (1.0 / n)
    h = f / g
    d = g * h + p
    return dict(g=g, p=p, b=b, G=G, B=B, P=P, F=F, n=n, f=f, h=h, d=d,
                D=float(np.sum(d)))


def stage_sweep(F, p_avg, max_n=MAX_STAGES):
    """给定总努力 F，扫描级数 N，D(N) = N*F^(1/N) + N*p_avg。"""
    ns = np.arange(1, max_n + 1)
    return ns, ns * F ** (1.0 / ns) + ns * p_avg


def continuous_n_opt(F, p_avg):
    """求解 ln f = 1 + p/f，再取 N_opt = ln F / ln f。"""
    f_opt = 3.59
    for _ in range(50):
        f_opt = np.exp(1.0 + p_avg / f_opt)
    return np.log(F) / np.log(f_opt), f_opt


def main():
    m = path_metrics(PATH, H_PATH)
    ns, d_sweep = stage_sweep(m["F"], m["P"] / m["n"])
    n_best = int(ns[int(np.argmin(d_sweep))])
    n_cont, f_opt = continuous_n_opt(m["F"], m["P"] / m["n"])

    print("逻辑努力示例（门延迟单位 tau；示例参数，不是 STA 签核结果）")
    print("  门库: " + ", ".join(f"{k}(g={v[0]:.2f}, p={v[1]:.0f})"
                                for k, v in GATES.items()))
    print("  路径: " + " -> ".join(f"{name}(b={b:.1f})" for name, b in PATH))
    print(f"\n  G={m['G']:.3f}, B={m['B']:.3f}, H={H_PATH:.1f}, "
          f"F={m['F']:.2f}, P={m['P']:.1f}, N={m['n']}")
    print(f"  等努力分配: f=F^(1/N)={m['f']:.3f}, D={m['D']:.3f} tau")

    print("\n  级  门       g       b       h      f=g*h    p      d(tau)")
    for i in range(m["n"]):
        name = PATH[i][0]
        print(f"  {i + 1:2d}  {name:6s}  {m['g'][i]:6.3f}  {m['b'][i]:6.3f}  "
              f"{m['h'][i]:6.3f}  {m['g'][i] * m['h'][i]:6.3f}  "
              f"{m['p'][i]:5.2f}  {m['d'][i]:6.3f}")

    print(f"\n  FO4: d_FO4 = 5 tau = {FO4_DELAY_PS:.1f} ps -> tau = {TAU_PS:.2f} ps")
    print(f"  路径延迟约 {m['D'] * TAU_PS:.1f} ps = {m['D'] / 5.0:.2f} 个 FO4")
    print("\n  N   D(tau)   delay(ps)")
    for n, d in zip(ns, d_sweep):
        print(f"  {n:2d}  {d:7.2f}  {d * TAU_PS:9.1f}")
    print(f"\n  整数最优级数 N_opt={n_best}；连续近似 N_opt={n_cont:.2f} "
          f"(f_opt={f_opt:.2f})；当前路径 N={m['n']}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8))
    stages = np.arange(1, m["n"] + 1)
    effort = m["g"] * m["h"]
    ax1.bar(stages, effort, label="effort g*h")
    ax1.bar(stages, m["p"], bottom=effort, label="parasitic p")
    ax1.set_xticks(stages, [name for name, _ in PATH])
    ax1.set(ylabel="Stage delay (tau)", title="(a) Per-stage delay")
    ax1.grid(axis="y", alpha=0.3)
    ax1.legend(fontsize=9)

    ax2.plot(ns, d_sweep, "o-", label="D(N)")
    ax2.axvline(m["n"], color="C2", ls="--", label=f"actual N={m['n']}")
    ax2.plot(n_best, d_sweep[n_best - 1], "o", ms=9, color="C3",
             label=f"best N={n_best}")
    ax2.set(xlabel="Number of stages N", ylabel="Path delay (tau)",
            title="(b) Path delay vs stage count")
    ax2.grid(alpha=0.3)
    ax2.legend(fontsize=9)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "logic_effort.png", dpi=150)
    plt.close(fig)
    print(f"  图已保存: {OUT_DIR / 'logic_effort.png'}")


if __name__ == "__main__":
    main()
