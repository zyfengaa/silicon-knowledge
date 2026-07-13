"""
full_adder_sim.py

Bit-level simulation of half adder, full adder, and 4-bit ripple-carry adder.
Prints step-by-step computation.
"""


def half_adder(a: int, b: int) -> tuple:
    """Half adder: adds two bits. Returns (sum, carry)."""
    assert a in (0, 1) and b in (0, 1), "Inputs must be 0 or 1"
    s = a ^ b
    c = a & b
    return (s, c)


def full_adder(a: int, b: int, cin: int) -> tuple:
    """Full adder: adds three bits. Returns (sum, carry-out)."""
    assert a in (0, 1) and b in (0, 1) and cin in (0, 1), "Inputs must be 0 or 1"
    s = a ^ b ^ cin
    cout = (a & b) | (a & cin) | (b & cin)
    return (s, cout)


def full_adder_step(a: int, b: int, cin: int, label: str = "") -> tuple:
    """Full adder with printed step info. Returns (sum, carry-out)."""
    s, cout = full_adder(a, b, cin)
    prefix = f"[{label}] " if label else ""
    print(f"{prefix}{a} + {b} + cin={cin} -> sum={s}, cout={cout}")
    return (s, cout)


def four_bit_ripple_carry_adder(a3, a2, a1, a0, b3, b2, b1, b0):
    """4-bit ripple-carry adder. Returns (sum_bits, carry_out)."""
    print(f"\n--- 4-bit Ripple-Carry Adder ---")
    av = (a3 << 3) | (a2 << 2) | (a1 << 1) | a0
    bv = (b3 << 3) | (b2 << 2) | (b1 << 1) | b0
    print(f"  A = {a3}{a2}{a1}{a0}  ({av})")
    print(f"  B = {b3}{b2}{b1}{b0}  ({bv})")
    print(f"  Computing bit by bit (LSB first):")

    s0, c1 = full_adder_step(a0, b0, 0, "Bit 0")
    s1, c2 = full_adder_step(a1, b1, c1, "Bit 1")
    s2, c3 = full_adder_step(a2, b2, c2, "Bit 2")
    s3, c4 = full_adder_step(a3, b3, c3, "Bit 3")

    result = (s3 << 3) | (s2 << 2) | (s1 << 1) | s0
    total = av + bv
    print(f"\n  Result: {s3}{s2}{s1}{s0}")
    print(f"  Carry-out (C4): {c4}")
    print(f"  Full: {c4}{s3}{s2}{s1}{s0}")
    print(f"  Decimal: {av} + {bv} = {result} (expected {total})")

    overflow = c3 ^ c4
    print(f"  Overflow: c3={c3}, c4={c4} -> {'OVERFLOW' if overflow else 'none'}")

    return ((s3, s2, s1, s0), c4)


def half_adder_demo():
    """All possible half adder inputs."""
    print("=" * 50)
    print("Half Adder Demonstration")
    print("=" * 50)
    print("  A  B | Sum  Carry")
    print("  -----|----------")
    for a in (0, 1):
        for b in (0, 1):
            s, c = half_adder(a, b)
            print(f"  {a}  {b} |  {s}    {c}")
    print()


def full_adder_demo():
    """All possible full adder inputs."""
    print("=" * 50)
    print("Full Adder Demonstration")
    print("=" * 50)
    print("  A  B Cin | Sum  Cout")
    print("  ---------|----------")
    for a in (0, 1):
        for b in (0, 1):
            for cin in (0, 1):
                s, cout = full_adder(a, b, cin)
                print(f"  {a}  {b}  {cin}  |  {s}    {cout}")
    print()


def adder_chain(a_val: int, b_val: int):
    """Add two 4-bit unsigned numbers."""
    assert 0 <= a_val <= 15 and 0 <= b_val <= 15, "Values must be 0-15"
    a3 = (a_val >> 3) & 1
    a2 = (a_val >> 2) & 1
    a1 = (a_val >> 1) & 1
    a0 = a_val & 1
    b3 = (b_val >> 3) & 1
    b2 = (b_val >> 2) & 1
    b1 = (b_val >> 1) & 1
    b0 = b_val & 1
    four_bit_ripple_carry_adder(a3, a2, a1, a0, b3, b2, b1, b0)


if __name__ == "__main__":
    half_adder_demo()
    full_adder_demo()

    print("=" * 50)
    print("Example 4-bit Additions")
    print("=" * 50)

    adder_chain(7, 5)     # 7 + 5 = 12
    adder_chain(3, 8)     # 3 + 8 = 11
    adder_chain(11, 6)    # 11 + 6 = 17 (overflow)
    adder_chain(0, 0)     # 0 + 0 = 0
    adder_chain(15, 1)    # 15 + 1 = 16 (overflow)

    print("\nAll demonstrations complete.")
