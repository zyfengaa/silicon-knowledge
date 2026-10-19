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
  - RAW 冒险检测；forwarding 可开关
  - 有 forwarding 时：ALU-ALU RAW 不停顿，load-use 停顿 1 周期
  - 无 forwarding 时：RAW 需要等待生产者写回（ALU-ALU 通常 2 个停顿）
  - 分支条件求值；仅在实际跳转时冲刷 IF/ID（2 条指令）
  - 流水线状态表打印

用法：
  python -I pipeline_sim.py
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

        # 执行阶段计算出的结果（供功能模型和分支条件使用）
        self.value: Optional[int] = None

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

        # 功能模型：寄存器堆（x0 恒为 0）
        self.regs = [0] * 32

        # 统计
        self.cycle = 0
        self.completed = 0
        self.load_use_stalls = 0
        self.no_forward_stalls = 0
        self.control_stalls = 0
        self.forward_ex_mem = 0
        self.forward_mem_wb = 0
        self.branches_taken = 0
        self.branches_not_taken = 0

        # 记录历史（每条指令在 5 个阶段中的状态）
        self.history: List[List[Optional[str]]] = []

    # ── 运行 ──────────────────────────────────────────────────

    def run(self, max_cycles: int = 200):
        """运行模拟直到流水线为空且没有更多指令可取。"""
        # 第一个周期就应该处在 IF 阶段，而不是先空转一个周期。
        if self.fetch_idx < self.total:
            self.slot[0] = self.instructions[self.fetch_idx]
            self.fetch_idx += 1

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
        state: List[Optional[str]] = [None] * 5
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
            self._writeback(inst_wb)
            self.completed += 1
        self.slot[4] = None

        # ── 2. MEM → WB ──
        self.slot[4] = inst_mem  # 即使是 BUBBLE 也传播
        self.slot[3] = None

        # ── 3. EX → MEM（分支在这里判定） ──
        flushed = False
        if inst_ex is not None and not inst_ex.is_nop():
            # 先计算 EX 结果，供后续分支条件和 WB 使用
            if inst_ex.writes_register():
                inst_ex.value = self._compute_value(inst_ex, inst_mem, inst_wb)

            if inst_ex.branch or inst_ex.jump:
                taken = self._branch_taken(inst_ex, inst_mem, inst_wb)
                if taken:
                    self._handle_taken_branch(inst_ex)
                    flushed = True
                else:
                    self.branches_not_taken += 1

        self.slot[3] = inst_ex  # 即使是 BUBBLE 也传播
        self.slot[2] = None

        # 如果分支冲刷了 IF/ID, 后续步骤不应使用被冲刷的指令
        if flushed:
            inst_if = None
            inst_id = None

        # ── 4. ID → EX（数据冒险检测在此） ──
        if inst_id is not None and not inst_id.is_nop():
            hazard = self._data_hazard(inst_id, inst_ex, inst_mem, inst_wb)
            if hazard is not None:
                # 冻结 IF/ID，在 EX 插入气泡
                self.slot[2] = BUBBLE
                self.slot[1] = inst_id
                if hazard == "load_use":
                    self.load_use_stalls += 1
                else:
                    self.no_forward_stalls += 1
                # 不推进 IF，也不取新指令；下一周期重新检测
                return

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

    # ── 数据冒险检测 ──────────────────────────────────────────

    def _data_hazard(self, id_inst: Instruction,
                     ex_inst: Optional[Instruction],
                     mem_inst: Optional[Instruction],
                     wb_inst: Optional[Instruction]) -> Optional[str]:
        """
        检测 ID 阶段指令与流水线中生产者的 RAW 冒险。

        返回:
          None          —— 不需要停顿
          "load_use"    —— 有 forwarding 时的 load-use 停顿
          "no_forward"  —— 无 forwarding 时等待生产者写回
        """
        sources = []
        if id_inst.needs_rs1() and id_inst.rs1 != 0:
            sources.append(id_inst.rs1)
        if id_inst.needs_rs2() and id_inst.rs2 != 0:
            sources.append(id_inst.rs2)
        # 去重，避免同一个寄存器在 rs1/rs2 中被重复计数
        sources = list(dict.fromkeys(sources))
        if not sources:
            return None

        if self.enable_forwarding:
            # load 的结果在 MEM 末才可用；下一条指令在 EX 开始时需要它 → 停 1 周期。
            # 当前 EX 中的 load 是唯一无法用转发解决的来源。
            if (ex_inst is not None and not ex_inst.is_nop()
                    and ex_inst.mem_read and ex_inst.rd != 0
                    and ex_inst.rd in sources):
                return "load_use"

            # 其余 RAW 由 EX/MEM 或 MEM/WB 转发解决（只做统计）
            if (ex_inst is not None and not ex_inst.is_nop()
                    and ex_inst.writes_register() and ex_inst.rd in sources):
                self.forward_ex_mem += 1
            elif (mem_inst is not None and not mem_inst.is_nop()
                    and mem_inst.writes_register() and mem_inst.rd in sources):
                self.forward_mem_wb += 1
            # wb_inst 在本周期前半段写寄存器堆，ID 后半段读取，视为已就绪
            return None

        # 无 forwarding：必须等生产者写回寄存器堆。
        # 当前 EX 和 MEM 中的生产者都还没有写回；当前 WB 的可视为已就绪。
        for producer in (ex_inst, mem_inst):
            if (producer is not None and not producer.is_nop()
                    and producer.writes_register()
                    and producer.rd in sources):
                return "no_forward"
        return None

    # ── 分支处理 ──────────────────────────────────────────────

    def _read_reg(self, reg: int,
                  mem_inst: Optional[Instruction],
                  wb_inst: Optional[Instruction]) -> int:
        """读取寄存器；优先使用 EX/MEM、MEM/WB 中尚未写回的结果。"""
        if reg == 0:
            return 0
        for producer in (mem_inst, wb_inst):
            if (producer is not None and not producer.is_nop()
                    and producer.writes_register()
                    and producer.rd == reg
                    and producer.value is not None):
                return producer.value
        return self.regs[reg]

    def _branch_taken(self, inst: Instruction,
                      mem_inst: Optional[Instruction],
                      wb_inst: Optional[Instruction]) -> bool:
        """求值分支条件；jal/jalr 视为总是跳转。"""
        if inst.jump:
            return True
        if inst.op_type != OpType.BRANCH:
            return False

        a = self._read_reg(inst.rs1, mem_inst, wb_inst)
        b = self._read_reg(inst.rs2, mem_inst, wb_inst)
        name = inst.name.strip().lower()

        if name.startswith("beq"):
            return a == b
        if name.startswith("bne"):
            return a != b
        if name.startswith("blt"):
            return a < b
        if name.startswith("bge"):
            return a >= b
        # 未识别的分支助记符：按不跳转处理，避免凭空假设
        return False

    def _handle_taken_branch(self, branch_inst: Instruction):
        """处理实际跳转: 冲刷 IF, ID 阶段，并从目标地址重新取指。"""
        # 冲刷 IF 和 ID 阶段中的指令
        self.slot[0] = None
        self.slot[1] = None

        if branch_inst.op_type == OpType.JAL:
            target = branch_inst.pc + branch_inst.imm // 4
        elif branch_inst.op_type == OpType.JALR:
            # 简化：寄存器中存放的是指令索引（不是字节地址），
            # imm 仍按字节偏移换算成指令条数。
            base = self._read_reg(branch_inst.rs1,
                                  self.slot[3], self.slot[4])
            target = base + branch_inst.imm // 4
        else:
            target = branch_inst.pc + branch_inst.imm // 4

        target = max(0, min(target, self.total - 1))
        self.fetch_idx = target

        self.branches_taken += 1
        # 冲刷了 IF+ID 中的 2 条错误路径指令
        self.control_stalls += 2

    # ── 功能模型 ──────────────────────────────────────────────

    def _compute_value(self, inst: Instruction,
                       mem_inst: Optional[Instruction],
                       wb_inst: Optional[Instruction]) -> Optional[int]:
        """在 EX 阶段计算指令结果（简化功能模型，不建模真实内存内容）。"""
        if inst.op_type == OpType.ALU_IMM:
            base = 0 if inst.rs1 == 0 else self._read_reg(
                inst.rs1, mem_inst, wb_inst)
            return base + inst.imm
        if inst.op_type == OpType.ALU_REG:
            a = self._read_reg(inst.rs1, mem_inst, wb_inst)
            b = self._read_reg(inst.rs2, mem_inst, wb_inst)
            # 仅用于演示；不同 ALU 操作统一按加法近似
            return a + b
        if inst.op_type == OpType.LUI:
            return inst.imm
        if inst.op_type == OpType.LOAD:
            return 0  # 未建模内存内容
        if inst.op_type in (OpType.JAL, OpType.JALR):
            return inst.pc + 1
        return None

    def _writeback(self, inst: Instruction):
        """WB 阶段写回寄存器堆。"""
        if not inst.writes_register():
            return
        inst.value = inst.value if inst.value is not None else 0
        self.regs[inst.rd] = inst.value

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
        denom = max(self.completed, 1)
        cpi = tc / denom
        # 5 级流水线的填充/排空开销为 4 个周期
        steady = max(tc - 4, 0) / denom
        data_stalls = self.load_use_stalls + self.no_forward_stalls
        print(f"\n{'=' * 50}")
        print(f"模拟统计")
        print(f"{'=' * 50}")
        print(f"静态指令总数:    {self.total}")
        print(f"完成指令数:      {self.completed}")
        print(f"总周期数:        {tc}")
        print(f"本次运行 CPI:    {cpi:.4f}")
        print(f"稳态 CPI:        {steady:.4f}  (扣除 5 级流水线填充/排空)")
        print(f"数据冒险停顿:    {data_stalls}"
              f"  (load-use={self.load_use_stalls}, "
              f"无转发等待={self.no_forward_stalls})")
        print(f"控制冒险停顿:    {self.control_stalls}"
              f"  (跳转/误预测冲刷)")
        print(f"分支:            taken={self.branches_taken}, "
              f"not-taken={self.branches_not_taken}")
        print(f"转发次数:        EX/MEM→EX={self.forward_ex_mem}, "
              f"MEM/WB→EX={self.forward_mem_wb}")
        print(f"理想稳态 CPI:    1.0000")
        print(f"额外稳态 CPI:    {steady - 1.0:+.4f}")
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
        # sw rs2, imm(rs1): 基址是 x9, 数据是 x1
        ("sw   x1, 0(x9)",   OpType.STORE,   0, 9, 1, 0),
    ]), "Load-Use: lw x1 → add x1(需停1周期)"


def s_branch():
    return make_instrs([
        ("addi x1, x0, 10",  OpType.ALU_IMM, 1, 0, 0, 10),
        # beq x1, x1 必定跳转；目标 = pc + 8/4 = 3
        ("beq  x1, x1, 8",   OpType.BRANCH,  0, 1, 1, 8),
        ("sub  x3, x1, x2",  OpType.ALU_REG, 3, 1, 2, 0),
        ("or   x4, x0, x3",  OpType.ALU_REG, 4, 0, 3, 0),
        ("addi x5, x0, 99",  OpType.ALU_IMM, 5, 0, 0, 99),
    ]), "分支: beq 实际跳转 → 冲刷 IF/ID"


def s_mixed():
    return make_instrs([
        ("add  x1, x2, x3",  OpType.ALU_REG, 1, 2, 3, 0),
        ("lw   x2, 0(x4)",   OpType.LOAD,    2, 4, 0, 0),
        ("sub  x5, x1, x6",  OpType.ALU_REG, 5, 1, 6, 0),
        ("add  x7, x2, x8",  OpType.ALU_REG, 7, 2, 8, 0),
        ("and  x9, x1, x10", OpType.ALU_REG, 9, 1, 10, 0),
        ("or   x11, x12,x13",OpType.ALU_REG, 11, 12, 13, 0),
    ]), "混合: RAW+Load-Use"


def run(instructions, desc, enable_forwarding=True):
    print(f"\n{'#' * 60}")
    print(f"# {desc}")
    print(f"{'#' * 60}")
    sim = PipelineSim(instructions, enable_forwarding=enable_forwarding)
    sim.run(max_cycles=200)
    print(f"\n指令: [{', '.join(str(i) for i in instructions)}]\n")
    sim.print_pipeline_table()
    sim.print_stats()
    return sim


if __name__ == "__main__":
    for fn in [s_ideal, s_raw, s_loaduse, s_branch, s_mixed]:
        run(*fn())

    # 演示 forwarding 开关对同一段 RAW 代码的影响
    print(f"\n\n{'#' * 60}")
    print("# forwarding 开关对照: RAW 序列")
    print(f"{'#' * 60}")
    for fwd in (True, False):
        sim = PipelineSim(s_raw()[0], enable_forwarding=fwd)
        sim.run(max_cycles=200)
        print(f"forwarding={str(fwd):5s}  周期={len(sim.history):2d}  "
              f"完成={sim.completed}  "
              f"load-use停顿={sim.load_use_stalls}  "
              f"无转发等待={sim.no_forward_stalls}")
