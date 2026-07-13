#!/usr/bin/env python3
"""
pipeline_sim.py — 5 级流水线行为模拟器

模拟 RISC-V 5 级流水线 (IF/ID/EX/MEM/WB) 在连续指令序列上的执行过程。

模型：
  流水线用 5 个"槽位"表示，编号 0-4 分别对应 IF/ID/EX/MEM/WB。
  每个周期，指令依次向后移动一个槽位（WB 完成后离开流水线）。

  各槽位含义（每周期正在做什么）：
    slot[0] (IF):  取指
    slot[1] (ID):  译码 + 冒险检测
    slot[2] (EX):  执行 + 分支判定
    slot[3] (MEM): 访存
    slot[4] (WB):  写回

支持功能：
  - RAW 冒险 + 转发
  - Load-use 停顿
  - 分支预测 + 冲刷
  - 流水线状态表打印

用法：
  python pipeline_sim.py
"""

from enum import Enum, auto
from typing import List, Optional, Tuple


# ─── 指令类型 ────────────────────────────────────────────────

class OpType(Enum):
    ALU_REG = auto()
    ALU_IMM = auto()
    LOAD = auto()
    STORE = auto()
    BRANCH = auto()
    JAL = auto()
    JALR = auto()
    LUI = auto()
    NOP = auto()


class Instruction:
    """一条 RISC-V 指令。"""

    def __init__(self, name: str, op_type: OpType,
                 rd: int = 0, rs1: int = 0, rs2: int = 0,
                 imm: int = 0, pc: int = 0):
        self.name = name
        self.op_type = op_type
        self.rd = rd
        self.rs1 = rs1
        self.rs2 = rs2
        self.imm = imm
        self.pc = pc

        # 控制信号
        self.reg_write = op_type in (OpType.ALU_REG, OpType.ALU_IMM,
                                      OpType.LOAD, OpType.LUI,
                                      OpType.JAL, OpType.JALR)
        self.mem_read = (op_type == OpType.LOAD)
        self.mem_write = (op_type == OpType.STORE)
        self.branch = (op_type == OpType.BRANCH)
        self.jump = (op_type in (OpType.JAL, OpType.JALR))

    def __repr__(self) -> str:
        return self.name

    def is_nop(self) -> bool:
        return self.op_type == OpType.NOP

    def writes_register(self) -> bool:
        return self.reg_write and self.rd != 0

    def needs_rs1(self) -> bool:
        return self.op_type not in (OpType.LUI, OpType.JAL, OpType.NOP)

    def needs_rs2(self) -> bool:
        return self.op_type in (OpType.ALU_REG, OpType.STORE, OpType.BRANCH)


BUBBLE = Instruction("BUBBLE", OpType.NOP)


# ─── 5 级流水线模拟器 ────────────────────────────────────────

class PipelineSim:
    """5 级流水线行为模拟器。"""

    STAGE_NAMES = ["IF", "ID", "EX", "MEM", "WB"]

    def __init__(self, instructions: List[Instruction],
                 enable_forwarding: bool = True):
        self.instructions = instructions
        self.enable_forwarding = enable_forwarding
        self.total = len(instructions)

        # 流水线槽位: 0=IF, 1=ID, 2=EX, 3=MEM, 4=WB
        self.slot: List[Optional[Instruction]] = [None] * 5

        # 当前取指位置（指令列表索引）
        self.fetch_idx = 0

        # 统计
        self.cycle = 0
        self.completed = 0
        self.data_stalls = 0
        self.control_stalls = 0

        # 记录历史
        self.history: List[List[Optional[str]]] = []

    # ── 运行 ──────────────────────────────────────────────────

    def run(self, max_cycles: int = 200):
        """运行模拟直到流水线为空且没有更多指令可取。"""
        while self.cycle < max_cycles:
            if self._pipeline_empty() and self.fetch_idx >= self.total:
                break
            self.cycle += 1
            self._tick()
        return self.history

    def _pipeline_empty(self) -> bool:
        """检查流水线槽位是否全部为空。"""
        return all(s is None or s.is_nop() for s in self.slot)

    def _tick(self):
        """推进一个时钟周期。"""
        inst_if = self.slot[0]
        inst_id = self.slot[1]
        inst_ex = self.slot[2]
        inst_mem = self.slot[3]
        inst_wb = self.slot[4]

        # ── 记录当前状态（传播之前） ──
        state = [None] * 5
        for i in range(5):
            s = self.slot[i]
            if s is None:
                state[i] = None
            elif s.is_nop():
                state[i] = "BUBBLE"
            else:
                state[i] = s.name
        self.history.append(state)

        # ── 1. WB 阶段完成 ──
        if inst_wb is not None and not inst_wb.is_nop():
            self.completed += 1
        self.slot[4] = None

        # ── 2. MEM → WB ──
        self.slot[4] = inst_mem  # 即使是 BUBBLE 也传播
        self.slot[3] = None

        # ── 3. EX → MEM（分支在这里判定） ──
        flushed_if = False
        if inst_ex is not None and not inst_ex.is_nop():
            if inst_ex.branch or inst_ex.jump:
                self._handle_branch(inst_ex)
                flushed_if = True
        self.slot[3] = inst_ex  # 即使是 BUBBLE 也传播
        self.slot[2] = None

        # 如果分支冲刷了 IF, 后续步骤不应使用被冲刷的指令
        if flushed_if:
            inst_if = None
            inst_id = None

        # ── 4. ID → EX（load-use 检测在此） ──
        if inst_id is not None and not inst_id.is_nop():
            # 检测 load-use: 检查 EX 阶段（刚刚移走的）是否是 load
            # 实际上需要检查的是"上一周期 EX 中的指令"
            # 在 inst_ex 被移到 MEM 之前，它就是 EX 中的指令
            if self._is_load_use_hazard(inst_id, inst_ex):
                # 冻结: ID 保持, EX 插入气泡, IF 重取
                self.slot[2] = BUBBLE
                self.slot[1] = inst_id       # ID 保留当前指令
                self.data_stalls += 1
                # 不执行第 5 步: IF 保持（不递增 fetch_idx）
                # 也不执行第 6 步
                return

            # 正常推进
            self.slot[2] = inst_id
        else:
            self.slot[2] = None
        self.slot[1] = None

        # ── 5. IF → ID ──
        if inst_if is not None and not inst_if.is_nop():
            self.slot[1] = inst_if
        else:
            self.slot[1] = None

        # ── 6. IF 取新指令 ──
        if self.fetch_idx < self.total:
            self.slot[0] = self.instructions[self.fetch_idx]
            self.fetch_idx += 1
        else:
            self.slot[0] = None

    # ── 冒险检测 ──────────────────────────────────────────────

    def _is_load_use_hazard(self, id_inst: Instruction,
                            ex_inst: Optional[Instruction]) -> bool:
        """
        检测 load-use 冒险。

        条件: EX 阶段的指令是 lw (mem_read=True),
              且 ID 阶段指令需要 lw 的目标寄存器。
        """
        if ex_inst is None or ex_inst.is_nop():
            return False
        if not ex_inst.mem_read:
            return False
        if ex_inst.rd == 0:
            return False

        if id_inst.needs_rs1() and id_inst.rs1 == ex_inst.rd:
            return True
        if id_inst.needs_rs2() and id_inst.rs2 == ex_inst.rd:
            return True
        return False

    def _handle_branch(self, branch_inst: Instruction):
        """处理分支/跳转: 冲刷 IF, ID 阶段。"""
        # 冲刷 IF 和 ID 阶段中的指令
        self.slot[0] = None
        self.slot[1] = None

        # 跳转到目标地址
        if branch_inst.jump:
            # jal/jalr: 无条件跳转
            if branch_inst.op_type == OpType.JAL:
                target = branch_inst.pc + branch_inst.imm // 4
            else:
                # jalr: 简化为跳转到 imm
                target = 0
        else:
            # beq/bne: 条件分支
            target = branch_inst.pc + branch_inst.imm // 4

        target = max(0, min(target, self.total - 1))
        self.fetch_idx = target

        # 记录控制冒险停顿（冲刷了 IF+ID = 2 个气泡）
        self.control_stalls += 2

    # ── 打印 ──────────────────────────────────────────────────

    def print_pipeline_table(self):
        """打印流水线状态表。"""
        col_widths = [6]
        for name in self.STAGE_NAMES:
            col_widths.append(max(12, len(name)))
        for row in self.history:
            for i, s in enumerate(row):
                d = s if s else "---"
                if s == "BUBBLE":
                    d = "BUBBLE"
                col_widths[i + 1] = max(col_widths[i + 1], len(d))

        header = f"{'Cycle':>{col_widths[0]}} |"
        for i, name in enumerate(self.STAGE_NAMES):
            header += f" {name:^{col_widths[i + 1]}} |"
        print(header)
        print("-" * len(header))

        for ci, row in enumerate(self.history):
            line = f" {ci + 1:>{col_widths[0]-1}d} |"
            for i, s in enumerate(row):
                d = s if s else "---"
                if s == "BUBBLE":
                    d = "BUBBLE"
                line += f" {d:^{col_widths[i + 1]}} |"
            print(line)

    def print_stats(self):
        """打印统计。"""
        tc = len(self.history)
        if tc == 0 or self.total == 0:
            return
        cpi = tc / self.total
        print(f"\n{'=' * 50}")
        print(f"模拟统计")
        print(f"{'=' * 50}")
        print(f"指令总数:        {self.total}")
        print(f"总周期数:        {tc}")
        print(f"CPI:             {cpi:.4f}")
        print(f"数据冒险停顿:    {self.data_stalls}")
        print(f"控制冒险停顿:    {self.control_stalls}")
        print(f"理想 CPI:        1.0000")
        print(f"额外 CPI:        {cpi - 1:.4f}")
        print(f"{'=' * 50}")


# ─── 辅助: 构建指令 ──────────────────────────────────────────

def make_instrs(defs: List[Tuple]) -> List[Instruction]:
    """从元组列表构建指令。每个元组: (name, op_type, rd, rs1, rs2, imm)"""
    return [
        Instruction(name, op_type, rd=rd, rs1=rs1, rs2=rs2,
                    imm=imm, pc=i)
        for i, (name, op_type, rd, rs1, rs2, imm) in enumerate(defs)
    ]


# ─── 测试场景 ────────────────────────────────────────────────

def s_ideal():
    return make_instrs([
        ("addi x1, x0, 10",  OpType.ALU_IMM, 1, 0, 0, 10),
        ("addi x2, x0, 20",  OpType.ALU_IMM, 2, 0, 0, 20),
        ("addi x3, x0, 30",  OpType.ALU_IMM, 3, 0, 0, 30),
        ("addi x4, x0, 40",  OpType.ALU_IMM, 4, 0, 0, 40),
        ("addi x5, x0, 50",  OpType.ALU_IMM, 5, 0, 0, 50),
    ]), "理想序列: 5 条独立 addi"


def s_raw():
    return make_instrs([
        ("add  x1, x2, x3",   OpType.ALU_REG, 1, 2, 3, 0),
        ("sub  x4, x1, x5",   OpType.ALU_REG, 4, 1, 5, 0),
        ("and  x6, x1, x7",   OpType.ALU_REG, 6, 1, 7, 0),
        ("or   x8, x9, x10",  OpType.ALU_REG, 8, 9, 10, 0),
    ]), "RAW 序列: add x1 → sub/and x1(转发可解)"


def s_loaduse():
    return make_instrs([
        ("lw   x1, 0(x2)",   OpType.LOAD,    1, 2, 0, 0),
        ("add  x4, x1, x5",  OpType.ALU_REG, 4, 1, 5, 0),
        ("sub  x6, x7, x8",  OpType.ALU_REG, 6, 7, 8, 0),
        ("sw   x1, 0(x9)",   OpType.STORE,   0, 1, 9, 0),
    ]), "Load-Use: lw x1 → add x1(需停1周期)"


def s_branch():
    return make_instrs([
        ("addi x1, x0, 10",  OpType.ALU_IMM, 1, 0, 0, 10),
        ("beq  x1, x0, 8",   OpType.BRANCH,  0, 1, 0, 8),
        ("sub  x3, x1, x2",  OpType.ALU_REG, 3, 1, 2, 0),
        ("or   x4, x0, x3",  OpType.ALU_REG, 4, 0, 3, 0),
        ("addi x5, x0, 99",  OpType.ALU_IMM, 5, 0, 0, 99),
    ]), "分支: beq → 跳转冲刷"


def s_mixed():
    return make_instrs([
        ("add  x1, x2, x3",  OpType.ALU_REG, 1, 2, 3, 0),
        ("lw   x2, 0(x4)",   OpType.LOAD,    2, 4, 0, 0),
        ("sub  x5, x1, x6",  OpType.ALU_REG, 5, 1, 6, 0),
        ("add  x7, x2, x8",  OpType.ALU_REG, 7, 2, 8, 0),
        ("and  x9, x1, x10", OpType.ALU_REG, 9, 1, 10, 0),
        ("or   x11, x12,x13",OpType.ALU_REG, 11, 12, 13, 0),
    ]), "混合: RAW+Load-Use"


def run(instructions, desc):
    print(f"\n{'#' * 60}")
    print(f"# {desc}")
    print(f"{'#' * 60}")
    sim = PipelineSim(instructions, enable_forwarding=True)
    sim.run(max_cycles=200)
    print(f"\n指令: [{', '.join(str(i) for i in instructions)}]\n")
    sim.print_pipeline_table()
    sim.print_stats()


if __name__ == "__main__":
    for fn in [s_ideal, s_raw, s_loaduse, s_branch, s_mixed]:
        run(*fn())
