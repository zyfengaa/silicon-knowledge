#!/usr/bin/env python3
"""
Simple RISC-V Simulator (RV32I subset)

Simulates a small set of RV32I instructions: add, sub, lw, sw, beq, addi.
Shows register and memory state after each instruction.

Usage:
    python3 riscv_sim.py

The program simulated computes Fibonacci numbers iteratively.
"""

import struct


class RISC_V_Simulator:
    """A minimal RV32I simulator for educational purposes."""

    def __init__(self, memory_size=1024):
        # 32 general-purpose registers (x0 = zero hardwired)
        self.regs = [0] * 32

        # Program counter
        self.pc = 0

        # Memory (byte-addressable, little-endian)
        self.memory = bytearray(memory_size)

        # Instruction memory starts at address 0
        # Data memory follows after the program

        # Internal state for step-by-step display
        self.instruction_count = 0
        self.running = True

    def load_program(self, program_bytes, base_addr=0):
        """Load a program (list of 4-byte instructions) into memory."""
        for i, instr in enumerate(program_bytes):
            addr = base_addr + i * 4
            # Store as 4-byte little-endian
            struct.pack_into("<I", self.memory, addr, instr & 0xFFFFFFFF)

    def read_word(self, addr):
        """Read a 32-bit word from memory (little-endian)."""
        return struct.unpack_from("<I", self.memory, addr)[0]

    def write_word(self, addr, value):
        """Write a 32-bit word to memory (little-endian)."""
        struct.pack_into("<I", self.memory, addr, value & 0xFFFFFFFF)

    def sign_extend(self, value, bits):
        """Sign-extend a value to 32 bits."""
        if (value >> (bits - 1)) & 1:
            value |= ~((1 << bits) - 1)
        return value & 0xFFFFFFFF

    def decode_and_execute(self, instr):
        """Decode and execute a single RV32I instruction. Returns True if successful."""
        opcode = instr & 0x7F
        rd = (instr >> 7) & 0x1F
        funct3 = (instr >> 12) & 0x07
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x1F
        funct7 = (instr >> 25) & 0x7F

        # For I-type and S-type instructions, extract immediate
        imm_i = self.sign_extend(instr >> 20, 12)  # I-type immediate
        imm_s = self.sign_extend(
            ((instr >> 25) << 5) | ((instr >> 7) & 0x1F), 12
        )  # S-type immediate
        imm_b = self.sign_extend(
            ((instr >> 31) & 1) << 12              # inst[31] -> offset[12]
            | ((instr >> 7) & 1) << 11              # inst[7] -> offset[11]
            | ((instr >> 25) & 0x3F) << 5           # inst[30:25] -> offset[10:5]
            | ((instr >> 8) & 0x0F) << 1            # inst[11:8] -> offset[4:1]
            | 0,                                     # offset[0] = 0
            13,
        )  # B-type immediate (byte offset, PC-relative)

        # Track which register is written for display
        dest_reg = None

        # R-type instructions (opcode = 0x33)
        if opcode == 0x33:
            if funct3 == 0x00 and funct7 == 0x00:  # ADD
                result = (self.regs[rs1] + self.regs[rs2]) & 0xFFFFFFFF
                self.regs[rd] = result
                dest_reg = rd
                self._print_instr(f"ADD  x{rd}, x{rs1}, x{rs2}")

            elif funct3 == 0x00 and funct7 == 0x20:  # SUB
                result = (self.regs[rs1] - self.regs[rs2]) & 0xFFFFFFFF
                self.regs[rd] = result
                dest_reg = rd
                self._print_instr(f"SUB  x{rd}, x{rs1}, x{rs2}")

            elif funct3 == 0x07 and funct7 == 0x00:  # AND
                result = self.regs[rs1] & self.regs[rs2]
                self.regs[rd] = result
                dest_reg = rd
                self._print_instr(f"AND  x{rd}, x{rs1}, x{rs2}")

            elif funct3 == 0x06 and funct7 == 0x00:  # OR
                result = self.regs[rs1] | self.regs[rs2]
                self.regs[rd] = result
                dest_reg = rd
                self._print_instr(f"OR   x{rd}, x{rs1}, x{rs2}")

            elif funct3 == 0x04 and funct7 == 0x00:  # XOR
                result = self.regs[rs1] ^ self.regs[rs2]
                self.regs[rd] = result
                dest_reg = rd
                self._print_instr(f"XOR  x{rd}, x{rs1}, x{rs2}")

            else:
                print(f"Unknown R-type: funct3={funct3}, funct7={funct7}")
                return False

            # Zero register is always 0
            self.regs[0] = 0

        # I-type ALU instructions (opcode = 0x13)
        elif opcode == 0x13:
            if funct3 == 0x00:  # ADDI
                result = (self.regs[rs1] + imm_i) & 0xFFFFFFFF
                self.regs[rd] = result
                dest_reg = rd
                self._print_instr(f"ADDI x{rd}, x{rs1}, {imm_i}")

            elif funct3 == 0x07:  # ANDI
                result = self.regs[rs1] & imm_i
                self.regs[rd] = result
                dest_reg = rd
                self._print_instr(f"ANDI x{rd}, x{rs1}, {imm_i}")

            elif funct3 == 0x06:  # ORI
                result = self.regs[rs1] | imm_i
                self.regs[rd] = result
                dest_reg = rd
                self._print_instr(f"ORI  x{rd}, x{rs1}, {imm_i}")

            else:
                print(f"Unknown I-type ALU: funct3={funct3}")
                return False

            self.regs[0] = 0

        # LW (opcode = 0x03)
        elif opcode == 0x03 and funct3 == 0x02:
            addr = (self.regs[rs1] + imm_i) & 0xFFFFFFFF
            value = self.read_word(addr)
            self.regs[rd] = value
            dest_reg = rd
            self._print_instr(f"LW   x{rd}, {imm_i}(x{rs1})  # addr=0x{addr:X}, value={value}")
            self.regs[0] = 0

        # SW (opcode = 0x23) and funct3 = 010
        elif opcode == 0x23 and funct3 == 0x02:
            addr = (self.regs[rs1] + imm_s) & 0xFFFFFFFF
            self.write_word(addr, self.regs[rs2])
            self._print_instr(f"SW   x{rs2}, {imm_s}(x{rs1})  # addr=0x{addr:X}, value={self.regs[rs2]}")
            # No register write for SW

        # Branch instructions (opcode = 0x63)
        elif opcode == 0x63:
            taken = False
            if funct3 == 0x00:  # BEQ
                taken = (self.regs[rs1] == self.regs[rs2])
                self._print_instr(f"BEQ  x{rs1}, x{rs2}, offset={imm_b}", taken)

            elif funct3 == 0x01:  # BNE
                taken = (self.regs[rs1] != self.regs[rs2])
                self._print_instr(f"BNE  x{rs1}, x{rs2}, offset={imm_b}", taken)

            elif funct3 == 0x04:  # BLT
                s_rs1 = self.regs[rs1] if self.regs[rs1] < 0x80000000 else self.regs[rs1] - 0x100000000
                s_rs2 = self.regs[rs2] if self.regs[rs2] < 0x80000000 else self.regs[rs2] - 0x100000000
                taken = (s_rs1 < s_rs2)
                self._print_instr(f"BLT  x{rs1}, x{rs2}, offset={imm_b}", taken)

            else:
                print(f"Unknown branch: funct3={funct3}")
                return False

            if taken:
                # B-type immediate is in units of 2 bytes, shifted by 1
                # imm_b is already the actual byte offset
                self.pc = (self.pc + imm_b) & 0xFFFFFFFF
                return True  # Branch taken, PC already updated

            # If not taken, PC += 4 happens below

        # LUI (opcode = 0x37)
        elif opcode == 0x37:
            immediate = instr & 0xFFFFF000  # Upper 20 bits
            self.regs[rd] = immediate & 0xFFFFFFFF
            dest_reg = rd
            self._print_instr(f"LUI  x{rd}, 0x{immediate>>12:X}")
            self.regs[0] = 0

        # AUIPC (opcode = 0x17)
        elif opcode == 0x17:
            immediate = instr & 0xFFFFF000
            result = (self.pc + immediate) & 0xFFFFFFFF
            self.regs[rd] = result
            dest_reg = rd
            self._print_instr(f"AUIPC x{rd}, 0x{immediate>>12:X}")
            self.regs[0] = 0

        # JAL (opcode = 0x6F)
        elif opcode == 0x6F:
            # Extract J-type immediate
            imm_j = (
                ((instr >> 31) << 20)           # bit 20
                | (((instr >> 12) & 0xFF) << 12)  # bits 19:12
                | ((instr >> 20) & 0x01) << 11    # bit 11
                | (((instr >> 21) & 0x3FF) << 1)  # bits 10:1
            )
            imm_j = self.sign_extend(imm_j, 21)
            self.regs[rd] = (self.pc + 4) & 0xFFFFFFFF
            dest_reg = rd
            self.pc = (self.pc + imm_j) & 0xFFFFFFFF
            self._print_instr(f"JAL  x{rd}, offset={imm_j}")
            self.regs[0] = 0
            return True  # PC already updated

        # JALR (opcode = 0x67)
        elif opcode == 0x67 and funct3 == 0x00:
            target = (self.regs[rs1] + imm_i) & 0xFFFFFFFE  # Clear LSB
            self.regs[rd] = (self.pc + 4) & 0xFFFFFFFF
            dest_reg = rd
            self.pc = target
            self._print_instr(f"JALR x{rd}, x{rs1}, {imm_i}")
            self.regs[0] = 0
            return True  # PC already updated

        else:
            print(f"Unknown instruction: opcode=0x{opcode:07b}, full=0x{instr:08X}")
            return False

        # Default: PC += 4
        self.pc = (self.pc + 4) & 0xFFFFFFFF

        # Print register state if a register was written
        if dest_reg is not None:
            self._print_reg_state(dest_reg)

        return True

    def run(self, max_instructions=100):
        """Run the simulation until PC goes out of bounds or max instructions reached."""
        print("=" * 70)
        print("RISC-V RV32I Simulator")
        print("=" * 70)
        print()

        while self.running and self.instruction_count < max_instructions:
            if self.pc >= len(self.memory) - 4:
                print(f"PC=0x{self.pc:X} out of memory bounds. Halting.")
                break

            instr = self.read_word(self.pc)
            if instr == 0:
                print("Encountered zero instruction (NOP/empty). Halting.")
                break

            self.instruction_count += 1
            print(f"[{self.instruction_count:3d}] PC=0x{self.pc:08X}", end="  ")

            success = self.decode_and_execute(instr)
            if not success:
                print("Execution halted due to error.")
                break

        if self.instruction_count >= max_instructions:
            print(f"\nReached max instruction limit ({max_instructions}). Halting.")

        self._print_final_state()

    def _print_instr(self, instr_str, branch_taken=None):
        """Display the instruction being executed."""
        if branch_taken is not None:
            status = " TAKEN" if branch_taken else " NOT TAKEN"
            print(f"{instr_str:<40s}{status}")
        else:
            print(instr_str)

    def _print_reg_state(self, rd):
        """Display a compact view of registers that have changed."""
        pass  # We'll show regs at end

    def _print_final_state(self):
        """Print final register state."""
        print()
        print("-" * 70)
        print("Final Register State")
        print("-" * 70)
        for i in range(0, 32, 4):
            regs_line = ""
            for j in range(4):
                r = i + j
                if r == 0:
                    name = "zero"
                elif r == 1:
                    name = "ra"
                elif r == 2:
                    name = "sp"
                elif r == 3:
                    name = "gp"
                elif r == 4:
                    name = "tp"
                elif 5 <= r <= 7:
                    name = f"t{r-5}"
                elif r == 8:
                    name = "s0"
                elif r == 9:
                    name = "s1"
                elif 10 <= r <= 17:
                    name = f"a{r-10}"
                elif 18 <= r <= 27:
                    name = f"s{r-16}"
                else:
                    name = f"t{r-26}"
                val = self.regs[r]
                regs_line += f"x{r:2d}({name:>4}) = 0x{val:08X}  "
            print(regs_line)

        # Print memory used
        print()
        print("Data Memory (non-zero words):")
        found = False
        for addr in range(0, len(self.memory), 4):
            val = self.read_word(addr)
            if val != 0:
                print(f"  0x{addr:04X}: 0x{val:08X}")
                found = True
        if not found:
            print("  (all zero)")


def assemble_instruction(mnemonic, *args):
    """Helper to encode a small subset of RV32I instructions for the test program.

    This is a minimal assembler for the simulator's test program.
    For full assembly, use a real RISC-V assembler.
    """
    # Register mapping
    regs = {
        "x0": 0, "zero": 0,
        "x1": 1, "ra": 1,
        "x2": 2, "sp": 2,
        "x3": 3, "gp": 3,
        "x4": 4, "tp": 4,
        "x5": 5, "t0": 5,
        "x6": 6, "t1": 6,
        "x7": 7, "t2": 7,
        "x8": 8, "s0": 8, "fp": 8,
        "x9": 9, "s1": 9,
        "x10": 10, "a0": 10,
        "x11": 11, "a1": 11,
        "x12": 12, "a2": 12,
        "x13": 13, "a3": 13,
        "x14": 14, "a4": 14,
        "x15": 15, "a5": 15,
        "x16": 16, "a6": 16,
        "x17": 17, "a7": 17,
        "x18": 18, "s2": 18,
        "x19": 19, "s3": 19,
        "x20": 20, "s4": 20,
        "x21": 21, "s5": 21,
        "x22": 22, "s6": 22,
        "x23": 23, "s7": 23,
        "x24": 24, "s8": 24,
        "x25": 25, "s9": 25,
        "x26": 26, "s10": 26,
        "x27": 27, "s11": 27,
        "x28": 28, "t3": 28,
        "x29": 29, "t4": 29,
        "x30": 30, "t5": 30,
        "x31": 31, "t6": 31,
    }

    def reg(name):
        return regs.get(name, name if isinstance(name, int) else 0)

    mn = mnemonic.lower()

    if mn == "add":
        rd, rs1, rs2 = reg(args[0]), reg(args[1]), reg(args[2])
        return (0x33) | (rd << 7) | (0 << 12) | (rs1 << 15) | (rs2 << 20) | (0 << 25)

    elif mn == "sub":
        rd, rs1, rs2 = reg(args[0]), reg(args[1]), reg(args[2])
        return (0x33) | (rd << 7) | (0 << 12) | (rs1 << 15) | (rs2 << 20) | (0x20 << 25)

    elif mn == "addi":
        rd, rs1, imm = reg(args[0]), reg(args[1]), int(args[2])
        imm = imm & 0xFFF
        return (0x13) | (rd << 7) | (0 << 12) | (reg(rs1) << 15) | (imm << 20)

    elif mn == "lw":
        # lw rd, offset(rs1)
        rd = reg(args[0])
        if "(" in args[1]:
            offset, rs1 = args[1].split("(")
            rs1 = reg(rs1.rstrip(")"))
        else:
            rs1 = reg(args[1])
            offset = args[2]
        offset = int(offset) & 0xFFF
        return (0x03) | (rd << 7) | (2 << 12) | (rs1 << 15) | (offset << 20)

    elif mn == "sw":
        # sw rs2, offset(rs1)
        rs2 = reg(args[0])
        offset, rs1 = args[1].split("(")
        rs1 = reg(rs1.rstrip(")"))
        offset = int(offset)
        imm_11_5 = (offset >> 5) & 0x7F
        imm_4_0 = offset & 0x1F
        return (0x23) | (imm_4_0 << 7) | (2 << 12) | (reg(rs1) << 15) | (reg(rs2) << 20) | (imm_11_5 << 25)

    elif mn == "beq":
        rs1, rs2, offset = reg(args[0]), reg(args[1]), int(args[2])
        offset = offset & 0x1FFF  # 13-bit signed offset in bytes
        # B-type encoding: offset bits stored at:
        # inst[31]=offset[12], inst[30:25]=offset[10:5],
        # inst[11:8]=offset[4:1], inst[7]=offset[11]
        imm_12 = (offset >> 12) & 1
        imm_10_5 = (offset >> 5) & 0x3F
        imm_4_1 = (offset >> 1) & 0x0F
        imm_11 = (offset >> 11) & 1
        encoded = (0x63) | (imm_11 << 7) | (imm_4_1 << 8) | (0 << 12) | (reg(rs1) << 15) | (reg(rs2) << 20) | (imm_10_5 << 25) | (imm_12 << 31)
        return encoded & 0xFFFFFFFF

    elif mn == "bne":
        rs1, rs2, offset = reg(args[0]), reg(args[1]), int(args[2])
        offset = offset & 0x1FFF
        # B-type encoding: offset bits stored at:
        # inst[31]=offset[12], inst[30:25]=offset[10:5],
        # inst[11:8]=offset[4:1], inst[7]=offset[11]
        imm_12 = (offset >> 12) & 1
        imm_10_5 = (offset >> 5) & 0x3F
        imm_4_1 = (offset >> 1) & 0x0F
        imm_11 = (offset >> 11) & 1
        encoded = (0x63) | (imm_11 << 7) | (imm_4_1 << 8) | (1 << 12) | (reg(rs1) << 15) | (reg(rs2) << 20) | (imm_10_5 << 25) | (imm_12 << 31)
        return encoded & 0xFFFFFFFF

    elif mn == "lui":
        rd, imm20 = args[0], int(args[1])
        return (0x37) | (reg(rd) << 7) | ((imm20 & 0xFFFFF) << 12)

    elif mn == "jal":
        rd, offset = args[0], int(args[1])
        offset = offset & 0x1FFFFE  # 21-bit, must be even
        # J-type fields:
        # bit 31    = imm[20]
        # bits 30:21 = imm[10:1]
        # bit 20    = imm[11]
        # bits 19:12 = imm[19:12]
        # bit 11    = imm[11] -- wait, J-type has different arrangement
        # RISC-V J-type: [imm[20]|imm[10:1]|imm[11]|imm[19:12]|rd|opcode]
        # bits:      31     30:21     20     19:12    11:7   6:0
        imm_20 = (offset >> 20) & 1
        imm_10_1 = (offset >> 1) & 0x3FF
        imm_11 = (offset >> 11) & 1
        imm_19_12 = (offset >> 12) & 0xFF
        encoded = (0x6F) | (reg(rd) << 7) | (imm_19_12 << 12) | (imm_11 << 20) | (imm_10_1 << 21) | (imm_20 << 31)
        return encoded & 0xFFFFFFFF

    else:
        raise ValueError(f"Unknown mnemonic: {mnemonic}")


def build_program():
    """Build a test program.

    Program: Compute Fibonacci iteratively.
    High-level:
        n = 10
        a, b = 0, 1
        for i in range(n):
            a, b = b, a + b
        // result in x10 (a0)

    RISC-V assembly:
        addi  x10, x0, 0     # a = 0
        addi  x11, x0, 1     # b = 1
        addi  x12, x0, 10    # n = 10 (loop count)
        addi  x13, x0, 0     # i = 0

    loop:
        addi  x13, x13, 1     # i++
        add   x14, x10, x11   # temp = a + b
        addi  x10, x11, 0     # a = b
        addi  x11, x14, 0     # b = temp
        bne   x13, x12, loop  # if i != n, goto loop

        # Store result to memory for verification
        sw    x10, 0(x0)      # Mem[0] = result
        lw    x15, 0(x0)      # verify by reading it back

        # Infinite loop to end
        beq   x0, x0, end
    end:
        beq   x0, x0, end
    """
    program = []
    
    # Address offsets for branches (computed in instruction units)
    # We'll build manually and compute offsets
    
    # Instructions (PC = 0, 4, 8, ...):
    prog = [
        ("addi", "x10", "x0", "0"),     # 0:  a = 0
        ("addi", "x11", "x0", "1"),     # 4:  b = 1
        ("addi", "x12", "x0", "10"),    # 8:  n = 10
        ("addi", "x13", "x0", "0"),     # 12: i = 0
        # loop at PC=16:
        ("addi", "x13", "x13", "1"),    # 16: i++
        ("add", "x14", "x10", "x11"),   # 20: temp = a + b
        ("addi", "x10", "x11", "0"),    # 24: a = b
        ("addi", "x11", "x14", "0"),    # 28: b = temp
        ("bne", "x13", "x12", "-16"),    # 32: if i != n, goto loop (offset = -16 bytes = 4 insts back)
        ("sw", "x10", "0(x0)"),         # 36: Mem[0] = result
        ("lw", "x15", "0(x0)"),         # 40: x15 = Mem[0]
        # end at PC=44:
        ("beq", "x0", "x0", "0"),        # 44: end: beq x0, x0, 0 (loop to self)
    ]

    # Compute BNE offset: from PC=32, target is PC=16, so offset = 16 - 32 = -16
    # BEQ offset: from PC=44, target is PC=44, so offset = 0
    # RISC-V branch offset is in bytes (PC-relative), must be divisible by 2

    for mnemonic, *args in prog:
        try:
            instr = assemble_instruction(mnemonic, *args)
            program.append(instr)
        except ValueError as e:
            print(f"Error assembling {mnemonic} {args}: {e}")
            raise

    return program


def main():
    # Build and load the program
    sim = RISC_V_Simulator(memory_size=1024)
    program = build_program()
    sim.load_program(program, base_addr=0)

    # Run the simulation
    sim.run(max_instructions=100)

    # Print result
    print()
    print("=" * 70)
    print(f"Fibonacci(10) = {sim.regs[10]}")
    print("Expected: 55")
    print("=" * 70)


if __name__ == "__main__":
    main()
