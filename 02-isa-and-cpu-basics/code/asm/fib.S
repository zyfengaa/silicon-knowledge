# RISC-V Assembly: Recursive Fibonacci
# =====================================
# This program computes fib(n) recursively where n is passed in a0.
# The result is returned in a0.
#
# Calling convention:
#   x10 (a0) = argument n
#   x10 (a0) = return value fib(n)
#
# Register usage:
#   s0 = saved frame pointer
#   s1 = saved n (callee-saved)
#   ra = return address

.section .text
.globl fib

# fib(n) returns the nth Fibonacci number
# fib(0) = 0
# fib(1) = 1
# fib(n) = fib(n-1) + fib(n-2) for n >= 2
#
# Register map:
#   a0 (x10) = n (argument), also return value
#   s0 (x8)  = original frame pointer (callee-saved)
#   s1 (x9)  = saved n across recursive calls (callee-saved)
#   ra (x1)  = return address (caller-saved)

fib:
    # ---- Prologue: set up stack frame ----
    addi sp, sp, -16          # Allocate 16 bytes on stack (2 saved regs + padding)
    sw   ra, 12(sp)           # Save return address (caller-saved, must preserve)
    sw   s0, 8(sp)            # Save frame pointer (callee-saved, must preserve)
    sw   s1, 4(sp)            # Save s1 (callee-saved register)
    addi s0, sp, 16           # Set frame pointer to original sp

    # ---- Base case check ----
    addi s1, a0, 0            # Save n in s1 (callee-saved, persists across calls)

    # if n == 0: return 0
    beq  a0, x0, return_0     # Branch to return_0 if n == 0

    # if n == 1: return 1
    addi t0, x0, 1             # t0 = 1
    beq  a0, t0, return_1     # Branch to return_1 if n == 1

    # ---- Recursive case: fib(n) = fib(n-1) + fib(n-2) ----
    # Compute fib(n-1)
    addi a0, s1, -1           # Set argument to n-1
    jal  ra, fib              # Recursive call: fib(n-1)
    addi t1, a0, 0            # Save fib(n-1) result in t1

    # Compute fib(n-2)
    addi a0, s1, -2           # Set argument to n-2
    jal  ra, fib              # Recursive call: fib(n-2)
    add  a0, t1, a0           # Result: fib(n-1) + fib(n-2)

    j    epilogue              # Jump to epilogue

return_0:
    addi a0, x0, 0            # Return 0
    j    epilogue

return_1:
    addi a0, x0, 1            # Return 1
    j    epilogue

epilogue:
    # ---- Epilogue: restore and return ----
    lw   s1, 4(sp)            # Restore callee-saved s1
    lw   s0, 8(sp)            # Restore callee-saved s0/fp
    lw   ra, 12(sp)           # Restore return address
    addi sp, sp, 16           # Deallocate stack frame
    jalr x0, ra, 0            # Return to caller

.section .rodata
msg_fib: .string "fib(%d) = %d\n"

.section .text
.globl main
main:
    # ---- Main function: call fib(10) and print result ----
    addi sp, sp, -16          # Allocate stack space
    sw   ra, 12(sp)           # Save return address

    addi a0, x0, 10           # Compute fib(10)
    jal  ra, fib              # Call fib(n), result in a0

    # Halt (in simulation, just return)
    lw   ra, 12(sp)           # Restore return address
    addi sp, sp, 16           # Deallocate stack
    jalr x0, ra, 0            # Return to caller
