"""
ieee754_demo.py

Take a float input and show its IEEE 754 single-precision representation:
sign bit, exponent (biased and unbiased), mantissa with hidden bit.
"""

import struct
import sys


def float_to_ieee754_bits(value: float) -> int:
    """Pack a float into 32-bit IEEE 754 and return raw bits as int."""
    return struct.unpack('>I', struct.pack('>f', value))[0]


def analyze_ieee754(value: float):
    """Decompose a float into IEEE 754 single-precision fields."""
    bits = float_to_ieee754_bits(value)

    sign_bit = (bits >> 31) & 1
    exponent_bits = (bits >> 23) & 0xFF
    mantissa_bits = bits & 0x7FFFFF

    sign_str = "-" if sign_bit else "+"

    biased_exp = exponent_bits
    unbiased_exp = biased_exp - 127

    if biased_exp == 0:
        leading_bit = 0
        effective_exp = -126
        classification = "Denormalized"
    elif biased_exp == 255:
        if mantissa_bits == 0:
            classification = "Infinity"
        else:
            classification = "NaN"
        leading_bit = 1
        effective_exp = 0
    else:
        leading_bit = 1
        effective_exp = unbiased_exp
        classification = "Normalized"

    print("=" * 65)
    print(f"IEEE 754 Single-Precision Analysis: {value}")
    print("=" * 65)

    print(f"\nRaw 32-bit hex: 0x{bits:08X}")
    print(f"Raw 32-bit bin: {bits:032b}")

    print(f"\n--- Sign ---")
    print(f"  Bit: {sign_bit}")
    print(f"  Sign: {sign_str}")

    print(f"\n--- Exponent ---")
    print(f"  Binary: {exponent_bits:08b}")
    print(f"  Hex:    0x{exponent_bits:02X}")
    print(f"  Decimal (biased):   {biased_exp}")
    print(f"  Decimal (unbiased): E - 127 = {biased_exp} - 127 = {unbiased_exp}")

    print(f"\n--- Mantissa (Significand) ---")
    print(f"  Binary (23 bits): {mantissa_bits:023b}")
    print(f"  Hex:              0x{mantissa_bits:06X}")
    print(f"  Decimal:          {mantissa_bits}")

    print(f"\n--- Value Reconstruction ---")
    print(f"  Classification: {classification}")
    if classification in ("Normalized", "Denormalized"):
        mantissa_decimal = mantissa_bits / (1 << 23)
        significand = leading_bit + mantissa_decimal
        reconstructed = ((-1) ** sign_bit) * significand * (2 ** effective_exp)
        print(f"  Leading bit: {leading_bit} (implicit)")
        print(f"  Significand: {significand}")
        print(f"  Formula: ({sign_str}1) x {significand} x 2^{effective_exp}")
        print(f"  Reconstructed value: {reconstructed}")
        print(f"  Original value:      {value}")
        print(f"  Difference: {abs(reconstructed - value)}")
    elif classification == "Infinity":
        print(f"  {sign_str}Infinity")
    elif classification == "NaN":
        print(f"  NaN (payload: 0x{mantissa_bits:06X})")

    bit_str = f"{bits:032b}"
    print(f"\n--- Bit Layout ---")
    print(f"  {bit_str[0]} {bit_str[1:9]} {bit_str[9:32]}")
    print(f"  S Exponent    Mantissa")


def show_special_values():
    """Demonstrate IEEE 754 special values."""
    specials = [
        ("+0.0", 0.0),
        ("-0.0", -0.0),
        ("+inf", float('inf')),
        ("-inf", float('-inf')),
        ("NaN", float('nan')),
        ("Smallest normalized", 1.17549435e-38),
        ("Largest normalized", 3.40282347e+38),
        ("Smallest positive (denorm)", 1.40129846e-45),
    ]
    print("\n" + "=" * 65)
    print("Special IEEE 754 Values")
    print("=" * 65)
    for name, val in specials:
        bits = float_to_ieee754_bits(val)
        print(f"\n  {name:35s}: 0x{bits:08X}")


def show_precision_issue():
    """Demonstrate that 0.1 is not exact."""
    print("\n" + "=" * 65)
    print("Precision Demo: Why 0.1 is not exact")
    print("=" * 65)
    sum_10 = sum(0.1 for _ in range(10))
    print(f"\n  0.1 + ... + 0.1 (10 times) = {sum_10}")
    print(f"  Exact decimal:              1.0")
    print(f"  Error:                      {sum_10 - 1.0}")


def interactive_mode():
    """User can enter floats for analysis."""
    print("\nEnter floats to analyze (or 'q' to quit):")
    while True:
        try:
            inp = input("\nfloat> ").strip()
            if inp.lower() in ('q', 'quit', 'exit'):
                break
            analyze_ieee754(float(inp))
        except ValueError:
            print("Invalid float.")


if __name__ == "__main__":
    demo_values = [0.0, 1.0, -1.0, 5.75, 0.1, 3.14159265, 42.0]

    for v in demo_values:
        analyze_ieee754(v)
        print()

    show_special_values()
    show_precision_issue()

    if len(sys.argv) > 1:
        print("\nAnalyzing command-line argument:")
        try:
            analyze_ieee754(float(sys.argv[1]))
        except ValueError:
            print(f"Cannot parse '{sys.argv[1]}' as float.")
