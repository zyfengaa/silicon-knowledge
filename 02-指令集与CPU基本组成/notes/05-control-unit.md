# 模块 02：指令集与 CPU 基本组成
## 05 — 控制单元设计

### 控制单元的作用

控制单元产生用于指挥数据通路（datapath）的控制信号。对于每条指令，它必须为以下信号设置正确的值：

| 控制信号 | 功能 |
|-------------------|--------------------------------------------------------------|
| RegWrite          | 使能对寄存器堆（register file）的写入（1 = 写入）                    |
| ALUSrcA           | 选择 ALU 的 A 输入（00 = RD1，01 = PC，10 = 零）            |
| ALUSrc            | 选择 ALU 的 B 输入（0 = 寄存器 RD2，1 = 立即数）         |
| MemWrite          | 使能对数据存储器的写入（1 = 存储）                      |
| MemRead           | 使能对数据存储器的读取（1 = 加载）                      |
| MemtoReg          | 选择写回数据（0 = ALU 结果，1 = 存储器数据）     |
| PCtoReg           | 选择 PC+4 作为写回数据（1 = PC+4，用于 JAL/JALR）      |
| ALUOp             | ALU 操作码（2 位，编码操作类别）     |
| Branch            | 使能分支目标选择（1 = 分支指令）      |
| Jump              | 使能跳转目标选择（1 = 跳转指令）          |
| PCSrc             | 选择下一个 PC（0 = PC+4，1 = 分支/跳转/ALU 目标）        |

### 硬连线控制与微程序控制

| 方面               | 硬连线控制（hardwired control）                               | 微程序控制（microprogrammed control）                    |
|----------------------|-------------------------------------------------|--------------------------------------------|
| 实现方式       | 组合逻辑门                       | ROM + 微定序器（microsequencer）                       |
| 速度                | 快（关键路径 = 门延迟）              | 较慢（ROM 访问 + 定序）           |
| 灵活性          | 难以修改（需重新设计逻辑）            | 易于修改（更改微代码）          |
| 设计复杂度    | 复杂指令集架构（ISA）下较高                           | 复杂指令集架构下较低                     |
| 应用场合              | RISC CPU、简单流水线                     | CISC CPU（1990 年前的 x86、VAX、68000）     |
| 示例              | RISC-V 单周期、MIPS、ARM Cortex-M         | Intel 486、VAX-11/780                      |

RISC-V 通常采用硬连线控制，因为其指令集架构简单且规整。现代 x86 CPU 在运行时将 CISC 指令解码为微操作（micro-ops），这是一种混合方法。

### 控制信号的生成

对于单周期 RISC-V CPU，控制信号通过以下方式生成：
1. 解码 **opcode** 位 [6:0] 以识别指令类别
2. 使用 **funct3** 和 **funct7**（对于 R 型指令）细化为具体的 ALU 操作
3. 将它们组合成逻辑方程或真值表

### RV32I 控制信号真值表

下表为每种指令类别给出控制信号取值。"X" = 无关项（don't care）。

| 指令 | opcode   | RegWrite | ALUSrcA | ALUSrc | MemWrite | MemRead | MemtoReg | PCtoReg | Branch | Jump | ALUOp |
|-------------|----------|----------|---------|--------|----------|---------|----------|---------|--------|------|-------|
| R 型      | 0110011  | 1        | 00      | 0      | 0        | 0       | 0        | 0       | 0      | 0    | 10    |
| I 型 ALU  | 0010011  | 1        | 00      | 1      | 0        | 0       | 0        | 0       | 0      | 0    | 10    |
| LW          | 0000011  | 1        | 00      | 1      | 0        | 1       | 1        | 0       | 0      | 0    | 00    |
| SW          | 0100011  | 0        | 00      | 1      | 1        | 0       | X        | 0       | 0      | 0    | 00    |
| BEQ/BNE/B* | 1100011  | 0        | 00      | 0      | 0        | 0       | X        | 0       | 1      | 0    | 01    |
| LUI         | 0110111  | 1        | 10      | 1      | 0        | 0       | 0        | 0       | 0      | 0    | 00    |
| AUIPC       | 0010111  | 1        | 01      | 1      | 0        | 0       | 0        | 0       | 0      | 0    | 00    |
| JAL         | 1101111  | 1        | X       | X      | 0        | 0       | X        | 1       | 0      | 1    | XX    |
| JALR        | 1100111  | 1        | 00      | 1      | 0        | 0       | X        | 1       | 0      | 1    | 00    |

对于 LUI 和 AUIPC，ALU 的 B 输入是由立即数扩展器（immediate extender）产生的 U 型立即数 `imm[31:12] << 12`。LUI 计算 `0 + imm`（ALUSrcA = zero）；AUIPC 计算 `PC + imm`（ALUSrcA = PC）。JAL 的目标地址来自 PC+imm 加法器，因此其 ALU 相关字段为无关项（表中展示了一个合法取值 X）。

#### 信号定义

**RegWrite**：若该指令写入寄存器堆，则为 1。
- R 型、I 型 ALU、LW、LUI、AUIPC、JAL、JALR = 1
- SW 与分支指令 = 0
- JAL/JALR 总是置位 RegWrite；对 x0 的写入会被寄存器堆直接丢弃，因此 `jalr x0, ...` 不需要特殊情况的解码。

**ALUSrcA**：选择 ALU 的第一个操作数。
- 00 = RD1（寄存器 rs1）
- 01 = PC
- 10 = 零（供 LUI 使用）
- R 型、I 型、LW、SW、分支指令、JALR = 00；AUIPC = 01；LUI = 10

**ALUSrc**：选择 ALU 的第二个操作数。
- 0 = 来自寄存器堆的 RD2（rs2）
- 1 = 立即数值（来自指令编码）
- R 型、分支指令 = 0；I 型、LW、SW、LUI、AUIPC、JALR = 1

**MemWrite**：数据存储器的写使能。仅对存储（store）指令置位。

**MemRead**：数据存储器的读使能。仅对加载（load）指令置位。

**MemtoReg**：当 PCtoReg = 0 时，选择写入寄存器堆的数据。
- 0 = ALU 结果
- 1 = 数据存储器输出（仅用于加载指令）

**PCtoReg**：选择 PC+4 作为写回值。
- 1 = 将 PC+4 写入 rd（JAL/JALR 的链接值）
- 0 = 使用 MemtoReg 的选择（ALU 结果或存储器数据）
- 正是这个额外的多路选择器（mux），使得同一数据通路能够为跳转指令写入 `PC+4`，而为其他所有情况写入 `ALU/memory` 数据。

**Branch**：分支指令（BEQ、BNE 等）为 1。ALU 执行比较；比较结果与由 funct3 选择的条件相组合，为条件成立的分支（taken branch）生成实际的 PCSrc 信号。

**Jump**：JAL 和 JALR 为 1。无论比较结果如何，都强制 PCSrc = 1。

**ALUOp**：两位编码，用于选择 ALU 控制单元如何生成具体的 ALU 操作：
- 00 = ADD（加载/存储的地址计算，以及 LUI/AUIPC/JALR 的高位立即数算术）
- 01 = 分支比较（由 funct3 选择 SUB/SLT/SLTU）
- 10 = R 型/I 型（由 funct3/funct7 解码）

### ALU 控制逻辑

ALU 控制模块接收 ALUOp、funct3、funct7 和 opcode，以产生精确的 ALU 操作。

| ALUOp | 指令类别 | funct3 | funct7[5] | ALU 操作 | ALU 控制 |
|-------|-------------------|--------|-----------|---------------|-------------|
| 00    | LW/SW/LUI/AUIPC/JALR | X   | X         | ADD           | 0000（ADD）  |
| 01    | BEQ/BNE           | 00x    | X         | SUB（比较） | 0001（SUB）  |
| 01    | BLT/BGE           | 10x    | X         | SLT（有符号）  | 0010（SLT）  |
| 01    | BLTU/BGEU         | 11x    | X         | SLTU（无符号）| 0011（SLTU）|
| 10    | R 型            | 000    | 0         | ADD           | 0000        |
| 10    | R 型            | 000    | 1         | SUB           | 0001        |
| 10    | R 型            | 010    | 0         | SLT           | 0010        |
| 10    | R 型            | 011    | 0         | SLTU          | 0011        |
| 10    | R 型            | 100    | 0         | XOR           | 0100        |
| 10    | R 型            | 110    | 0         | OR            | 0110        |
| 10    | R 型            | 111    | 0         | AND           | 0111        |
| 10    | R 型            | 001    | 0         | SLL           | 1000        |
| 10    | R 型            | 101    | 0         | SRL           | 1001        |
| 10    | R 型            | 101    | 1         | SRA           | 1010        |
| 10    | I 型            | 000    | X         | ADD           | 0000        |
| 10    | I 型            | 010    | X         | SLTI          | 0010        |
| 10    | I 型            | 011    | X         | SLTIU         | 0011        |
| 10    | I 型            | 100    | X         | XORI          | 0100        |
| 10    | I 型            | 110    | X         | ORI           | 0110        |
| 10    | I 型            | 111    | X         | ANDI          | 0111        |

精确的 ALU 控制编码由具体实现定义；此处对 SLT/SLTU 一致采用 0010/0011。ALU 还必须产生 `Zero`、`Less`（有符号）和 `LessU`（无符号）比较标志，因为分支单元需要的不只是 `Zero`。

### PCSrc 的生成

最终的 PC 来源选择为：

```
cmp      = funct3[2:1]                  // 00 = equal, 10 = signed less, 11 = unsigned less
base     = (cmp == 00) ? Zero
         : (cmp == 10) ? Less
         :               LessU
BranchCond = funct3[0] ? ~base : base   // bit 0 distinguishes eq/ne, lt/ge, ltu/geu

PCSrc = Jump | (Branch & BranchCond)
```

其中：
- BEQ (funct3=000): base = Zero, BranchCond = Zero
- BNE (funct3=001): base = Zero, BranchCond = ~Zero
- BLT (funct3=100): base = Less, BranchCond = Less
- BGE (funct3=101): base = Less, BranchCond = ~Less
- BLTU (funct3=110): base = LessU, BranchCond = LessU
- BGEU (funct3=111): base = LessU, BranchCond = ~LessU
- JAL/JALR：Jump=1，无条件选择跳转目标

注意，仅将 `Branch & Zero` 连线的设计无法实现 BLT/BGE/BLTU/BGEU；ALU 必须提供有符号和无符号比较标志，分支单元必须根据 funct3 在它们之间进行选择。

### 控制信号的逻辑方程

在硬件描述语言（hardware description language，Verilog/VHDL）中，控制单元可以表示为组合逻辑：

```verilog
always_comb begin
    // Defaults
    RegWrite = 0;  ALUSrcA = 2'b00;  ALUSrc = 0;  MemWrite = 0;
    MemRead = 0;   MemtoReg = 0;     PCtoReg = 0; Branch = 0;
    Jump = 0;      ALUOp = 2'b00;

    case (opcode)
        7'b0110011: begin              // R-type
            RegWrite = 1;  ALUOp = 2'b10;
        end
        7'b0010011: begin              // I-type ALU
            RegWrite = 1;  ALUSrc = 1;  ALUOp = 2'b10;
        end
        7'b0000011: begin              // LW
            RegWrite = 1;  ALUSrc = 1;  MemRead = 1;
            MemtoReg = 1;  ALUOp = 2'b00;
        end
        7'b0100011: begin              // SW
            ALUSrc = 1;  MemWrite = 1;  ALUOp = 2'b00;
        end
        7'b1100011: begin              // Branch
            Branch = 1;  ALUOp = 2'b01;
        end
        7'b1101111: begin              // JAL
            RegWrite = 1;  Jump = 1;  PCtoReg = 1;
            // target comes from the PC+imm adder; ALU fields are don't-care
        end
        7'b1100111: begin              // JALR
            RegWrite = 1;  ALUSrcA = 2'b00;  ALUSrc = 1;
            Jump = 1;  PCtoReg = 1;  ALUOp = 2'b00;
        end
        7'b0110111: begin              // LUI
            RegWrite = 1;  ALUSrcA = 2'b10;  ALUSrc = 1;  ALUOp = 2'b00;
        end
        7'b0010111: begin              // AUIPC
            RegWrite = 1;  ALUSrcA = 2'b01;  ALUSrc = 1;  ALUOp = 2'b00;
        end
    endcase
end
```

### 控制单元框图

```
+-------------+     +-----------------------+
| instruction |     |     Control Unit       |
|   [6:0]     |---->|    (Main Decoder)     |----> RegWrite
|   (opcode)  |     |                        |----> MemWrite
|             |     |                        |----> MemRead
|   [14:12]   |     |                        |----> ALUSrcA[1:0]
|   (funct3)  |     |                        |----> ALUSrc
|             |     |                        |----> MemtoReg
|   [31:25]   |     |                        |----> PCtoReg
|   (funct7)  |     |                        |----> Branch
|             |     |                        |----> Jump
|             |     |                        |----> ALUOp[1:0]
|             |     +------+-----------------+
+-------------+            |
                           | ALUOp, funct3, funct7
                           v
                    +--------------+
                    | ALU Decoder  |----> ALU control[3:0]
                    +--------------+
```

### 小结

- 控制单元将指令位转换为数据通路的控制信号
- 硬连线控制 = 快速、简单，适合 RISC 指令集架构
- 微程序控制 = 灵活、复杂，适用于 CISC 指令集架构
- 控制信号由 opcode、funct3 和 funct7 字段推导而来
- ALUOp 是一个 2 位中间编码，可简化 ALU 控制解码器
- 单周期 RISC-V 控制单元的真值表相对较小（9 种指令类别）

---

### 参考文献

1. Patterson, D. A., & Hennessy, J. L. *Computer Organization and Design: The Hardware/Software Interface*. RISC-V Edition. Morgan Kaufmann. Chapter 4, Sections 4.3--4.4.
2. Harris, S., & Harris, D. *Digital Design and Computer Architecture: RISC-V Edition*. Morgan Kaufmann, 2021. Chapter 7, Section 7.3.3.
3. Waterman, A., & Asanovic, K. (Eds.). *The RISC-V Instruction Set Manual, Volume I: Unprivileged Architecture*. Document Version 20191213.
4. Patterson, D. A. "Microprogramming." *Scientific American*, Vol. 248 No. 3, 1983.
