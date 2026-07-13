#!/usr/bin/env python3
"""
pipeline_perf.py — 流水线性能分析工具

给定指令序列和场景参数，计算并比较不同场景下的 CPI：
  1. 理想流水线 (无冒险)
  2. 有数据冒险 + 转发
  3. 有数据冒险 + 控制冒险

支持从指令序列进行 RAW 依赖分析，并基于分支比例估算 CPI。
"""

from typing import List, Tuple
from pipeline_sim import Instruction, OpType, PipelineSim


# ─── 性能模型 ────────────────────────────────────────────────

class PipelinePerformanceModel:
    """基于指令流特征的 CPI 分析模型。"""

    def __init__(self, instructions: List[Instruction]):
        self.instructions = instructions
        self.n = len(instructions)

        # 指令类型统计
        self._count_types()

    def _count_types(self):
        """统计指令序列中各类指令的数量和比例。"""
        self.alu_count = 0
        self.load_count = 0
        self.store_count = 0
        self.branch_count = 0
        self.jump_count = 0
        self.other_count = 0

        for inst in self.instructions:
            if inst.op_type in (OpType.ALU_REG, OpType.ALU_IMM, OpType.LUI):
                self.alu_count += 1
            elif inst.op_type == OpType.LOAD:
                self.load_count += 1
            elif inst.op_type == OpType.STORE:
                self.store_count += 1
            elif inst.op_type == OpType.BRANCH:
                self.branch_count += 1
            elif inst.op_type in (OpType.JAL, OpType.JALR):
                self.jump_count += 1
            else:
                self.other_count += 1

    def get_type_ratios(self) -> dict:
        """返回各指令类型比例。"""
        return {
            'alu':   self.alu_count   / max(self.n, 1),
            'load':  self.load_count  / max(self.n, 1),
            'store': self.store_count / max(self.n, 1),
            'branch': self.branch_count / max(self.n, 1),
            'jump':  self.jump_count  / max(self.n, 1),
        }

    def analyze_raw_dependencies(self) -> List[Tuple[int, int, int]]:
        """
        分析 RAW 依赖。

        返回: [(依赖指令索引, 被依赖指令索引, 依赖类型), ...]
          依赖类型: 1 = EX转发可解, 2 = load-use(需停顿)
        """
        raws: List[Tuple[int, int, int]] = []

        for i, inst in enumerate(self.instructions):
            if inst.is_nop():
                continue

            # 检查 rs1 (源操作数 1)
            if inst.needs_rs1() and inst.rs1 != 0:
                self._find_raw_source(i, inst.rs1, raws)

            # 检查 rs2 (源操作数 2)
            if inst.needs_rs2() and inst.rs2 != 0:
                self._find_raw_source(i, inst.rs2, raws)

        return raws

    def _find_raw_source(self, curr_idx: int, reg: int,
                         raws: List[Tuple[int, int, int]]):
        """寻找写寄存器 reg 的最近前一条指令。"""
        for j in range(curr_idx - 1, max(curr_idx - 10, -1), -1):
            prev = self.instructions[j]
            if prev.is_nop():
                continue
            if prev.writes_register() and prev.rd == reg:
                # 判断依赖类型
                # 如果前一条是 load → load-use 冒险
                if prev.op_type == OpType.LOAD:
                    dep_type = 2  # load-use, 需要停顿
                else:
                    dep_type = 1  # ALU → ALU, 转发可解决
                raws.append((curr_idx, j, dep_type))
                return  # 只找最近的写入者
            # 如果前一条指令也要写同一个寄存器，但更远的依赖
            # 实际上依赖链会覆盖，所以找到最近的即可

    def compute_ideal_cpi(self) -> float:
        """理想流水线 CPI = 1.0。"""
        return 1.0

    def compute_data_hazard_cpi(self) -> float:
        """
        计算数据冒险导致的 CPI 损失。

        假设:
          - 转发解决所有非 load-use 的 RAW 依赖 (无停顿)
          - 每次 load-use 需要 1 个停顿周期
        """
        raws = self.analyze_raw_dependencies()
        load_use_stalls = sum(1 for _, _, dep_type in raws if dep_type == 2)
        return load_use_stalls / max(self.n, 1)

    def compute_control_hazard_cpi(
        self,
        branch_ratio: float = None,
        predictor_accuracy: float = 0.90,
        branch_penalty: int = 2
    ) -> float:
        """
        计算控制冒险导致的 CPI 损失。

        参数:
          predictor_accuracy: 分支预测准确率 (0~1)
          branch_penalty: 预测错误代价 (周期数)
        """
        if branch_ratio is None:
            branch_ratio = self.get_type_ratios()['branch']

        mispredict_rate = 1.0 - predictor_accuracy
        return branch_ratio * mispredict_rate * branch_penalty

    def compute_total_cpi(
        self,
        predictor_accuracy: float = 0.90,
        branch_penalty: int = 2
    ) -> dict:
        """
        计算在不同场景下的 CPI。

        返回:
          {
            'ideal':                {cpi, desc},
            'data_only':            {cpi, desc},
            'data_and_control':     {cpi, desc},
          }
        """
        ideal = self.compute_ideal_cpi()
        data_cpi_loss = self.compute_data_hazard_cpi()
        control_cpi_loss = self.compute_control_hazard_cpi(
            predictor_accuracy=predictor_accuracy,
            branch_penalty=branch_penalty
        )

        return {
            'ideal': {
                'cpi': ideal,
                'desc': '理想流水线（无冒险）'
            },
            'data_only': {
                'cpi': ideal + data_cpi_loss,
                'desc': f'数据冒险 + 转发（load-use 停顿 = {data_cpi_loss:.4f}）'
            },
            'data_and_control': {
                'cpi': ideal + data_cpi_loss + control_cpi_loss,
                'desc': (f'数据冒险 + 控制冒险'
                         f'（load-use={data_cpi_loss:.4f}, '
                         f'分支={control_cpi_loss:.4f}）')
            },
        }


# ─── 显示函数 ────────────────────────────────────────────────

def print_analysis(instructions: List[Instruction], title: str,
                   predictor_accuracy: float = 0.90,
                   branch_penalty: int = 2):
    """分析指令序列并打印 CPI 对比表。"""
    model = PipelinePerformanceModel(instructions)
    ratios = model.get_type_ratios()
    raws = model.analyze_raw_dependencies()

    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")

    # 显示指令序列
    print(f"\n指令序列 ({len(instructions)} 条):")
    for i, inst in enumerate(instructions):
        print(f"  [{i:2d}] {inst}")

    # 显示指令类型分布
    print(f"\n指令类型分布:")
    alu = model.alu_count
    load = model.load_count
    store = model.store_count
    branch = model.branch_count
    jump = model.jump_count
    print(f"  ALU/R-type:      {alu:3d} ({ratios['alu']*100:5.1f}%)")
    print(f"  Load:            {load:3d} ({ratios['load']*100:5.1f}%)")
    print(f"  Store:           {store:3d} ({ratios['store']*100:5.1f}%)")
    print(f"  Branch:          {branch:3d} ({ratios['branch']*100:5.1f}%)")
    print(f"  Jump:            {jump:3d} ({ratios['jump']*100:5.1f}%)")

    # 显示 RAW 依赖
    print(f"\nRAW 依赖检测:")
    if raws:
        for curr, prev, dep_type in raws:
            curr_inst = instructions[curr]
            prev_inst = instructions[prev]
            dep_name = "Load-Use" if dep_type == 2 else "RAW (转发)"
            print(f"  [{curr}] {curr_inst}  ←  [{prev}] {prev_inst}  [{dep_name}]")
    else:
        print(f"  (无 RAW 依赖)")

    # 显示 CPI 对比
    print(f"\nCPI 对比分析 (预测准确率={predictor_accuracy}, 分支代价={branch_penalty}):")
    print(f"  {'场景':<40s} {'CPI':>8s} {'额外':>8s}")
    print(f"  {'-'*58}")

    results = model.compute_total_cpi(
        predictor_accuracy=predictor_accuracy,
        branch_penalty=branch_penalty
    )

    for key in ['ideal', 'data_only', 'data_and_control']:
        r = results[key]
        extra = r['cpi'] - 1.0
        print(f"  {r['desc']:<40s} {r['cpi']:>8.4f} {extra:>+8.4f}")

    return results


def print_comparison_table(scenarios: List[Tuple[List[Instruction], str]],
                           predictor_accuracy: float = 0.90,
                           branch_penalty: int = 2):
    """多场景对比表格。"""
    print(f"\n\n{'#' * 70}")
    print(f"# 多场景 CPI 对比总表")
    print(f"# 分支预测准确率={predictor_accuracy}, 分支错误代价={branch_penalty}")
    print(f"{'#' * 70}")

    header = f"{'场景':<35s} {'指令数':>6s} {'理想 CPI':>9s} {'数据 CPI':>9s} {'总 CPI':>9s}"
    print(f"\n{header}")
    print(f"{'-' * 70}")

    rows = []
    for instructions, desc in scenarios:
        model = PipelinePerformanceModel(instructions)
        raws = model.analyze_raw_dependencies()
        results = model.compute_total_cpi(
            predictor_accuracy=predictor_accuracy,
            branch_penalty=branch_penalty
        )
        ideal = results['ideal']['cpi']
        data = results['data_only']['cpi']
        total = results['data_and_control']['cpi']

        short_desc = desc[:33]
        print(f"{short_desc:<35s} {len(instructions):>6d} {ideal:>9.4f} {data:>9.4f} {total:>9.4f}")


# ─── 测试场景 ────────────────────────────────────────────────

def make_branch_test_sequence() -> List[Instruction]:
    """含分支指令的测试序列。"""
    return [
        Instruction("addi x1, x0, 10", OpType.ALU_IMM, rd=1, rs1=0, imm=10),
        Instruction("addi x2, x0, 1",  OpType.ALU_IMM, rd=2, rs1=0, imm=1),
        Instruction("beq  x1, x0, 8",  OpType.BRANCH,  rs1=1, rs2=0, imm=8),
        Instruction("sub  x3, x1, x2", OpType.ALU_REG, rd=3, rs1=1, rs2=2),
        Instruction("addi x1, x1, -1", OpType.ALU_IMM, rd=1, rs1=1, imm=-1),
        Instruction("jal  x0, -12",    OpType.JAL,     rd=0, imm=-12),
        Instruction("or   x4, x0, x3", OpType.ALU_REG, rd=4, rs1=0, rs2=3),
    ]


def make_load_intensive_sequence() -> List[Instruction]:
    """高比例 load 序列。"""
    return [
        Instruction("lw   x1, 0(x2)",  OpType.LOAD,    rd=1, rs1=2, imm=0),
        Instruction("lw   x3, 4(x2)",  OpType.LOAD,    rd=3, rs1=2, imm=4),
        Instruction("add  x5, x1, x3", OpType.ALU_REG, rd=5, rs1=1, rs2=3),
        Instruction("sw   x5, 8(x2)",  OpType.STORE,   rs1=5, rs2=2, imm=8),
        Instruction("lw   x6, 8(x2)",  OpType.LOAD,    rd=6, rs1=2, imm=8),
        Instruction("addi x7, x6, 1",  OpType.ALU_IMM, rd=7, rs1=6, imm=1),
        Instruction("sw   x7, 12(x2)", OpType.STORE,   rs1=7, rs2=2, imm=12),
        Instruction("lw   x8, 12(x2)", OpType.LOAD,    rd=8, rs1=2, imm=12),
        Instruction("add  x9, x8, x0", OpType.ALU_REG, rd=9, rs1=8, rs2=0),
    ]


def make_no_hazard_sequence() -> List[Instruction]:
    """无依赖的独立指令序列。"""
    return [
        Instruction("addi x1, x0, 1",  OpType.ALU_IMM, rd=1, rs1=0, imm=1),
        Instruction("addi x2, x0, 2",  OpType.ALU_IMM, rd=2, rs1=0, imm=2),
        Instruction("addi x3, x0, 3",  OpType.ALU_IMM, rd=3, rs1=0, imm=3),
        Instruction("addi x4, x0, 4",  OpType.ALU_IMM, rd=4, rs1=0, imm=4),
        Instruction("addi x5, x0, 5",  OpType.ALU_IMM, rd=5, rs1=0, imm=5),
        Instruction("or   x6, x1, x2", OpType.ALU_REG, rd=6, rs1=1, rs2=2),
        Instruction("and  x7, x3, x4", OpType.ALU_REG, rd=7, rs1=3, rs2=4),
        Instruction("sub  x8, x6, x7", OpType.ALU_REG, rd=8, rs1=6, rs2=7),
    ]


def make_test_instructions_local() -> List[Instruction]:
    """创建基础的 RISC-V 测试指令序列。"""
    return [
        Instruction("add  x1, x2, x3",   OpType.ALU_REG, rd=1, rs1=2, rs2=3),
        Instruction("lw   x1, 0(x2)",    OpType.LOAD,    rd=1, rs1=2, imm=0),
        Instruction("sub  x4, x1, x5",   OpType.ALU_REG, rd=4, rs1=1, rs2=5),
        Instruction("add  x7, x1, x8",   OpType.ALU_REG, rd=7, rs1=1, rs2=8),
        Instruction("or   x6, x7, x8",   OpType.ALU_REG, rd=6, rs1=7, rs2=8),
        Instruction("addi x9, x0, 10",   OpType.ALU_IMM, rd=9, rs1=0, imm=10),
    ]


# ─── 主入口 ──────────────────────────────────────────────────

if __name__ == "__main__":
    scenarios = [
        (make_test_instructions_local(), "基础测试序列"),
        (make_no_hazard_sequence(),    "无 RAW 依赖序列"),
        (make_load_intensive_sequence(), "高 load 密度序列"),
        (make_branch_test_sequence(),   "含分支指令序列"),
    ]

    # 逐场景分析
    for instructions, desc in scenarios:
        print_analysis(instructions, desc,
                       predictor_accuracy=0.90, branch_penalty=2)

    # 对比总表
    print_comparison_table(scenarios,
                           predictor_accuracy=0.90, branch_penalty=2)

    # 参数敏感性分析
    print(f"\n\n{'#' * 60}")
    print(f"# 参数敏感性分析：分支预测准确率对 CPI 的影响")
    print(f"{'#' * 60}")

    instructions = make_branch_test_sequence()
    model = PipelinePerformanceModel(instructions)

    print(f"\n场景: {desc}")
    print(f"{'准确率':>8s} {'理想 CPI':>9s} {'数据 CPI':>9s} {'总 CPI':>9s}")
    print(f"{'-' * 40}")

    for acc in [0.50, 0.70, 0.80, 0.85, 0.90, 0.95, 0.99]:
        results = model.compute_total_cpi(predictor_accuracy=acc, branch_penalty=2)
        total = results['data_and_control']['cpi']
        data = results['data_only']['cpi']
        ideal = results['ideal']['cpi']
        print(f"{acc:>7.0%} {ideal:>9.4f} {data:>9.4f} {total:>9.4f}")
