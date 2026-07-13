# RISC-V Assembly: Memory Access with Different Addressing Modes
# ==============================================================
# This file demonstrates the various addressing modes available
# in RV32I for load and store instructions, along with common
# memory access patterns.
#
# RISC-V memory addressing modes:
#   1. Base + offset (register + immediate)  -- lw/sw rd, offset(rs1)
#   2. Register indirect (register + 0)      -- lw/sw rd, 0(rs1)
#   3. PC-relative (for branches/jumps)      -- beq/jal
#   4. Immediate (for lui/auipc + addi)      -- load address into register
#
# NOTE: RISC-V does NOT have pre/post-increment, scaled index,
# or absolute addressing modes. Complex addresses must be
# computed explicitly with add/mul instructions.

.section .data
.align 4

# Define some test data in memory
array_data:
    .word 10, 20, 30, 40, 50, 60, 70, 80, 90, 100
array_end:

msg_ok:     .string "Memory access tests passed.\n"
msg_fail:   .string "Memory access test FAILED.\n"

.section .text
.globl main

# ============================================================
# 1. Base + Offset Addressing Mode (the standard mode)
#
# Effective address = value in rs1 + sign-extended immediate
# The immediate is a 12-bit signed value (-2048 to +2047)
#
# This is the ONLY addressing mode for loads and stores in RISC-V.
# ============================================================

base_plus_offset_example:
    # Load the address of array_data into a register
    lui  t0, %hi(array_data)    # t0 = upper 20 bits of array_data address
    addi t0, t0, %lo(array_data) # t0 = full address of array_data

    # Base + offset: load element at index 0 (offset 0)
    lw   t1, 0(t0)              # t1 = Mem[t0 + 0]  = array[0] = 10

    # Base + offset: load element at index 1 (offset 4)
    lw   t2, 4(t0)              # t2 = Mem[t0 + 4]  = array[1] = 20

    # Base + offset: load element at index 2 (offset 8)
    lw   t3, 8(t0)              # t3 = Mem[t0 + 8]  = array[2] = 30

    # Negative offset: load from address before the base
    lw   t4, -4(t0)             # t4 = Mem[t0 - 4]  (whatever is before array)

    # Store with base + offset: modify array[0]
    addi t1, x0, 99             # t1 = 99
    sw   t1, 0(t0)              # array[0] = 99

    # Verify the store worked
    lw   t5, 0(t0)              # t5 = array[0] (should be 99)
    addi t6, x0, 99             # t6 = 99
    bne  t5, t6, test_failed    # Fail if not equal

    jalr x0, ra, 0              # Return

# ============================================================
# 2. Register Indirect (Offset = 0)
#
# This is just base + offset with imm = 0.
# Effective address = value in rs1.
# ============================================================

register_indirect_example:
    lui  t0, %hi(array_data)
    addi t0, t0, %lo(array_data)

    # Load from address in register (offset = 0)
    lw   t1, 0(t0)              # t1 = Mem[t0] -- indirect addressing

    # Store to address in register (offset = 0)
    addi t2, x0, 77             # t2 = 77
    sw   t2, 0(t0)              # Mem[t0] = 77 -- indirect store

    jalr x0, ra, 0

# ============================================================
# 3. Array Indexing (scaled index computed manually)
#
# RISC-V has no scaled-index addressing mode (like x86's [reg + reg*4]).
# The index must be multiplied by the element size explicitly.
# ============================================================

array_indexing_example:
    lui  t0, %hi(array_data)     # t0 = base address of array
    addi t0, t0, %lo(array_data)

    # Access array[i] where i = 5 (word array, so offset = i * 4)
    addi t1, x0, 5              # t1 = i = 5 (index)
    slli t2, t1, 2              # t2 = i * 4 = 20 (shift left 2 = multiply by 4)
    add  t3, t0, t2             # t3 = base + i*4 = address of array[5]
    lw   t4, 0(t3)              # t4 = array[5] = 60

    # Write to array[i]:
    addi t5, x0, 42             # t5 = 42
    sw   t5, 0(t3)              # array[5] = 42

    jalr x0, ra, 0

# ============================================================
# 4. PC-Relative Addressing (for branches and jumps)
#
# Branches (BEQ, BNE, BLT, BGE, BLTU, BGEU) and JAL use
# PC-relative addressing. The offset is added to PC.
# ============================================================

pc_relative_example:
    addi t0, x0, 0              # t0 = 0 (loop counter)
    addi t1, x0, 5              # t1 = 5 (loop limit)

pc_loop:
    addi t0, t0, 1              # t0++

    # PC-relative branch: if t0 < t1, go back to pc_loop
    blt  t0, t1, pc_loop        # PC = PC + (offset_to_pc_loop) if t0 < t1

    jalr x0, ra, 0

# ============================================================
# 5. Loading an Arbitrary Address (far data)
#
# For data that is far from the current PC, use LUI + ADDI
# to construct the full 32-bit address.
# ============================================================

load_far_address_example:
    # If the address is known at link time, the assembler/compiler
    # typically generates LUI + ADDI with %hi/%lo relocations.

    lui  t0, %hi(array_data)    # Upper 20 bits
    addi t0, t0, %lo(array_data) # Lower 12 bits

    # Now t0 holds the full 32-bit address. Load from it:
    lw   t1, 0(t0)              # Load from array_data

    # For a constant address known at assembly time:
    lui  t2, 0x12345             # t2 = 0x12345000 (page-aligned)
    addi t2, t2, 0x678           # t2 = 0x12345678
    lw   t3, 0(t2)              # Load from absolute address 0x12345678

    jalr x0, ra, 0

# ============================================================
# 6. Byte and Halfword Access (LB, LBU, LH, LHU, SB, SH)
#
# In addition to word access (LW/SW), RISC-V supports byte and
# halfword access with sign or zero extension.
# ============================================================

byte_halfword_example:
    lui  t0, %hi(array_data)
    addi t0, t0, %lo(array_data)

    # Load byte (sign-extended): LB
    lb   t1, 0(t0)              # t1 = sign_extend(Mem[t0+0]) = 10

    # Load byte (zero-extended): LBU
    lbu  t3, 0(t0)              # t3 = zero_extend(Mem[t0+0]) = 10

    # Load halfword (sign-extended): LH
    lh   t4, 0(t0)              # t4 = sign_extend(Mem[t0+0:t0+1]) = 10

    # Load halfword (zero-extended): LHU
    lhu  t5, 0(t0)              # t5 = zero_extend(Mem[t0+0:t0+1]) = 10

    # Store byte
    sb   t5, 0(t0)              # Store lower 8 bits of t5 to Mem[t0]

    # Store halfword
    sh   t5, 0(t0)              # Store lower 16 bits of t5 to Mem[t0]

    jalr x0, ra, 0

# ============================================================
# 7. Stack-Based Memory Access
#
# The stack pointer (sp, x2) is used for function call frames.
# All access is through base+offset addressing on sp.
# ============================================================

stack_access_example:
    # Allocate space on stack
    addi sp, sp, -32            # sp -= 32 (allocate 32 bytes)

    # Store values to stack locals (using sp as base)
    addi t0, x0, 100            # t0 = 100
    sw   t0, 0(sp)              # Mem[sp+0] = 100 (local variable 1)

    addi t1, x0, 200            # t1 = 200
    sw   t1, 4(sp)              # Mem[sp+4] = 200 (local variable 2)

    addi t2, x0, 300            # t2 = 300
    sw   t2, 8(sp)              # Mem[sp+8] = 300 (local variable 3)

    # Load them back
    lw   t3, 0(sp)              # t3 = 100
    lw   t4, 4(sp)              # t4 = 200
    lw   t5, 8(sp)              # t5 = 300

    # Verify
    addi t6, x0, 100
    bne  t3, t6, test_failed
    addi t6, x0, 200
    bne  t4, t6, test_failed
    addi t6, x0, 300
    bne  t5, t6, test_failed

    # Deallocate stack space
    addi sp, sp, 32             # sp += 32 (deallocate)

    jalr x0, ra, 0

# ============================================================
# 8. Memory Copy (memcpy-like pattern)
#
# Demonstrates a complete memory access pattern: copying
# data from source to destination using lw/sw.
# ============================================================

# Allocate destination buffer in data section
.section .bss
.align 4
dest_buffer:
    .space 40                  # 40 bytes (10 words)

.section .text
memcpy_example:
    lui  t0, %hi(array_data)    # t0 = source address
    addi t0, t0, %lo(array_data)
    lui  t1, %hi(dest_buffer)   # t1 = destination address
    addi t1, t1, %lo(dest_buffer)
    addi t2, x0, 10             # t2 = count (10 words)

copy_loop:
    beq  t2, x0, copy_done     # If count == 0, done
    lw   t3, 0(t0)              # t3 = *src
    sw   t3, 0(t1)              # *dst = t3
    addi t0, t0, 4              # src++ (in bytes)
    addi t1, t1, 4              # dst++ (in bytes)
    addi t2, t2, -1             # count--
    j    copy_loop

copy_done:
    jalr x0, ra, 0

# ============================================================
# Main entry point: run all examples
# ============================================================

main:
    addi sp, sp, -16
    sw   ra, 12(sp)

    jal  ra, base_plus_offset_example
    jal  ra, register_indirect_example
    jal  ra, array_indexing_example
    jal  ra, pc_relative_example
    jal  ra, load_far_address_example
    jal  ra, byte_halfword_example
    jal  ra, stack_access_example
    jal  ra, memcpy_example

    # All tests passed
    j    test_passed

test_failed:
    j    test_done

test_passed:
    j    test_done

test_done:
    lw   ra, 12(sp)
    addi sp, sp, 16
    jalr x0, ra, 0
