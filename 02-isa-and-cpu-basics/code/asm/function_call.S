# RISC-V Assembly: Function Call Convention
# ==========================================
# This file demonstrates the RISC-V calling convention with caller-saved
# and callee-saved registers, and proper stack frame management.
#
# RISC-V Calling Convention Summary:
#   Arguments:   a0-a7 (x10-x17)
#   Return:      a0 (x10)
#   Caller-saved: ra, t0-t6, a0-a7
#   Callee-saved: s0-s11 (x8-x9, x18-x27)
#   Stack grows: downward (sp decreases on allocation)

.section .text
.globl main

# ============================================================
# Example 1: Caller-saved register discipline
#
# The CALLER saves any registers it needs across a function call.
# This includes: ra, t0-t6, a0-a7
# ============================================================

caller_example:
    # This function calls another function and needs to preserve
    # its own values across the call.

    addi sp, sp, -16          # Allocate 16 bytes on stack
    sw   ra, 12(sp)           # Save return address (caller-saved)

    # Load some values into t-registers (caller-saved)
    addi t0, x0, 42           # t0 = 42 (caller-saved, will be lost across call)
    addi t1, x0, 100          # t1 = 100 (caller-saved)

    # Before calling another function, save t0 and t1 if we need them
    sw   t0, 8(sp)            # Save t0 on stack (caller saves it)
    sw   t1, 4(sp)            # Save t1 on stack

    # Call another function (clobbers t0, t1, a0-a7, ra)
    addi a0, x0, 5            # Set argument a0 = 5
    jal  ra, callee_func      # Call callee_func(5)

    # After return, restore caller-saved registers
    lw   t1, 4(sp)            # Restore t1
    lw   t0, 8(sp)            # Restore t0

    # Now we can use t0 and t1 with their original values
    add  t2, t0, t1           # t2 = 42 + 100 = 142

    # Restore return address and return
    lw   ra, 12(sp)           # Restore return address
    addi sp, sp, 16           # Deallocate stack
    jalr x0, ra, 0            # Return

# ============================================================
# Example 2: Callee-saved register discipline
#
# The CALLEE saves any s-registers it modifies and restores them
# before returning. This preserves the caller's values transparently.
# ============================================================

callee_func:
    # This function uses callee-saved registers that the caller
    # expects to remain unchanged.

    # Prologue: save callee-saved registers
    addi sp, sp, -20          # Allocate 20 bytes: ra + 2 saved regs + locals
    sw   ra, 16(sp)           # Save return address (needed for nested calls)
    sw   s0, 12(sp)           # Save s0 (callee-saved, caller expects it preserved)
    sw   s1, 8(sp)            # Save s1 (callee-saved)

    # Use callee-saved registers freely
    addi s0, a0, 0            # s0 = a0 (save argument in callee-saved reg)
    addi s1, x0, 0            # s1 = 0 (counter)

loop_start:
    # Simple loop: multiply s0 by 2 repeated 3 times
    addi s1, s1, 1            # s1++ (counter)
    slli s0, s0, 1            # s0 = s0 << 1 (multiply by 2)

    addi t0, x0, 3            # t0 = 3 (loop limit)
    blt  s1, t0, loop_start   # if s1 < 3, continue loop

    # Set return value
    addi a0, s0, 0            # a0 = s0 (modified value)

    # Epilogue: restore callee-saved registers (in reverse order)
    lw   s1, 8(sp)            # Restore s1 to original value
    lw   s0, 12(sp)           # Restore s0 to original value
    lw   ra, 16(sp)           # Restore return address
    addi sp, sp, 20           # Deallocate stack
    jalr x0, ra, 0            # Return

# ============================================================
# Example 3: Stack frame with local variables
#
# Demonstrates a complete stack frame with saved registers,
# frame pointer, and local variable storage.
# ============================================================

# Function: sum_and_product(int a, int b, int* sum_out, int* prod_out)
# Arguments:
#   a0 = first operand
#   a1 = second operand
#   a2 = pointer to store sum (optional)
#   a3 = pointer to store product (optional)
# Returns: a0 = sum (also written to *sum_out if non-NULL)

sum_and_product:
    # Prologue with frame pointer
    addi sp, sp, -16          # Allocate stack frame
    sw   ra, 12(sp)           # Save return address
    sw   s0, 8(sp)            # Save frame pointer / callee-saved
    addi s0, sp, 16           # Set frame pointer (points to saved ra)

    # Compute sum
    add  t0, a0, a1           # t0 = a + b (sum)

    # Compute product
    mul  t1, a0, a1           # t1 = a * b (product)

    # Check if sum_out is non-null
    beq  a2, x0, skip_sum     # If sum_out == NULL, skip store
    sw   t0, 0(a2)            # *sum_out = sum

skip_sum:
    # Check if prod_out is non-null
    beq  a3, x0, skip_prod    # If prod_out == NULL, skip store
    sw   t1, 0(a3)            # *prod_out = product

skip_prod:
    # Return sum in a0
    addi a0, t0, 0            # a0 = sum

    # Epilogue
    lw   s0, 8(sp)            # Restore s0
    lw   ra, 12(sp)           # Restore return address
    addi sp, sp, 16           # Deallocate stack
    jalr x0, ra, 0            # Return

# ============================================================
# Example 4: Nested function calls with proper save/restore
#
# Demonstrates proper convention when calling functions from
# within functions (non-leaf function).
# ============================================================

# Function: compute(int x) -> computes x^2 + 2*x + 1 = (x+1)^2
compute:
    # Non-leaf function (calls multiply), must save ra
    addi sp, sp, -16
    sw   ra, 12(sp)           # Save ra because we call another function
    sw   s0, 8(sp)            # Save s0 because we use callee-saved

    addi s0, a0, 0            # s0 = x (save x in callee-saved reg)

    # Compute x + 1
    addi a0, s0, 1            # a0 = x + 1
    jal  ra, multiply         # Call multiply(x+1)

    # Result: a0 = (x+1) * (x+1) = (x+1)^2

    lw   s0, 8(sp)            # Restore s0
    lw   ra, 12(sp)           # Restore ra
    addi sp, sp, 16
    jalr x0, ra, 0            # Return

# Simple leaf function: multiplies a0 by itself (no stack frame needed)
multiply:
    mul  a0, a0, a0           # a0 = a0 * a0
    jalr x0, ra, 0            # Return (leaf function, no stack needed)

# ============================================================
# Main: Demonstrate all the conventions
# ============================================================

main:
    # Prologue
    addi sp, sp, -16
    sw   ra, 12(sp)

    # Call caller_example
    jal  ra, caller_example

    # Use sum_and_product
    addi sp, sp, -16          # Allocate local storage for outputs
    addi a0, x0, 7            # a0 = 7
    addi a1, x0, 3            # a1 = 3
    addi a2, sp, 0            # a2 = &local_sum (on stack)
    addi a3, sp, 4            # a3 = &local_prod (on stack)
    jal  ra, sum_and_product  # Call function

    # At this point:
    #   a0 = 10 (sum)
    #   local_sum (sp+0) = 10
    #   local_prod (sp+4) = 21

    addi sp, sp, 16           # Deallocate local storage

    # Epilogue
    lw   ra, 12(sp)
    addi sp, sp, 16
    jalr x0, ra, 0            # Exit
