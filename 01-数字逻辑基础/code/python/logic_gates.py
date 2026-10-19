"""
logic_gates.py

Python simulation of fundamental logic gates.
Each gate takes bit inputs (0 or 1) and returns a bit output (0 or 1).
Includes comprehensive test cases.
"""


def logic_and(a: int, b: int) -> int:
    """AND gate: output is 1 only when both inputs are 1."""
    assert a in (0, 1) and b in (0, 1), "Inputs must be 0 or 1"
    return a & b


def logic_or(a: int, b: int) -> int:
    """OR gate: output is 1 when at least one input is 1."""
    assert a in (0, 1) and b in (0, 1), "Inputs must be 0 or 1"
    return a | b


def logic_not(a: int) -> int:
    """NOT gate (inverter): output is the complement of the input."""
    assert a in (0, 1), "Input must be 0 or 1"
    return 1 - a


def logic_nand(a: int, b: int) -> int:
    """NAND gate: output is 0 only when both inputs are 1."""
    assert a in (0, 1) and b in (0, 1), "Inputs must be 0 or 1"
    return logic_not(logic_and(a, b))


def logic_nor(a: int, b: int) -> int:
    """NOR gate: output is 1 only when both inputs are 0."""
    assert a in (0, 1) and b in (0, 1), "Inputs must be 0 or 1"
    return logic_not(logic_or(a, b))


def logic_xor(a: int, b: int) -> int:
    """XOR gate: output is 1 when inputs differ."""
    assert a in (0, 1) and b in (0, 1), "Inputs must be 0 or 1"
    return a ^ b


def logic_xnor(a: int, b: int) -> int:
    """XNOR gate: output is 1 when inputs match."""
    assert a in (0, 1) and b in (0, 1), "Inputs must be 0 or 1"
    return logic_not(logic_xor(a, b))


def nand_as_not(a: int) -> int:
    """NAND configured as NOT: (A NAND A) = A'"""
    return logic_nand(a, a)


def nand_as_and(a: int, b: int) -> int:
    """NAND configured as AND: NOT(NAND(a,b))"""
    return nand_as_not(logic_nand(a, b))


def nand_as_or(a: int, b: int) -> int:
    """NAND configured as OR using De Morgan's: (a'.b')' = a+b"""
    return logic_nand(nand_as_not(a), nand_as_not(b))


def nor_as_not(a: int) -> int:
    """NOR configured as NOT: (A NOR A) = A'"""
    return logic_nor(a, a)


def nor_as_or(a: int, b: int) -> int:
    """NOR configured as OR: NOT(NOR(a,b))"""
    return nor_as_not(logic_nor(a, b))


def nor_as_and(a: int, b: int) -> int:
    """NOR configured as AND using De Morgan's: (a'+b')' = a.b"""
    return logic_nor(nor_as_not(a), nor_as_not(b))


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_basic_gates():
    """Test truth tables for all basic gates."""
    print("=" * 55)
    print("TEST: Basic Gate Truth Tables")
    print("=" * 55)

    test_vectors = [(0, 0), (0, 1), (1, 0), (1, 1)]

    expected_and = [0, 0, 0, 1]
    print("\nAND Gate:")
    for (a, b), exp in zip(test_vectors, expected_and):
        result = logic_and(a, b)
        status = "PASS" if result == exp else "FAIL"
        print(f"  {a} AND {b} = {result}  (expected {exp}) [{status}]")

    expected_or = [0, 1, 1, 1]
    print("\nOR Gate:")
    for (a, b), exp in zip(test_vectors, expected_or):
        result = logic_or(a, b)
        status = "PASS" if result == exp else "FAIL"
        print(f"  {a} OR {b} = {result}  (expected {exp}) [{status}]")

    print("\nNOT Gate:")
    for a in (0, 1):
        result = logic_not(a)
        exp = 1 - a
        status = "PASS" if result == exp else "FAIL"
        print(f"  NOT {a} = {result}  [{status}]")

    expected_nand = [1, 1, 1, 0]
    print("\nNAND Gate:")
    for (a, b), exp in zip(test_vectors, expected_nand):
        result = logic_nand(a, b)
        status = "PASS" if result == exp else "FAIL"
        print(f"  {a} NAND {b} = {result}  [{status}]")

    expected_nor = [1, 0, 0, 0]
    print("\nNOR Gate:")
    for (a, b), exp in zip(test_vectors, expected_nor):
        result = logic_nor(a, b)
        status = "PASS" if result == exp else "FAIL"
        print(f"  {a} NOR {b} = {result}  [{status}]")

    expected_xor = [0, 1, 1, 0]
    print("\nXOR Gate:")
    for (a, b), exp in zip(test_vectors, expected_xor):
        result = logic_xor(a, b)
        status = "PASS" if result == exp else "FAIL"
        print(f"  {a} XOR {b} = {result}  [{status}]")

    expected_xnor = [1, 0, 0, 1]
    print("\nXNOR Gate:")
    for (a, b), exp in zip(test_vectors, expected_xnor):
        result = logic_xnor(a, b)
        status = "PASS" if result == exp else "FAIL"
        print(f"  {a} XNOR {b} = {result}  [{status}]")


def test_universal_nand():
    """Demonstrate NAND universality."""
    print("\n" + "=" * 55)
    print("TEST: NAND Universality")
    print("=" * 55)

    test_vectors = [(0, 0), (0, 1), (1, 0), (1, 1)]

    print("\nNAND as NOT:")
    for a in (0, 1):
        r = nand_as_not(a)
        e = logic_not(a)
        print(f"  NAND-NOT({a}) = {r}  (= NOT {a}) [{'PASS' if r==e else 'FAIL'}]")

    print("\nNAND as AND:")
    for (a, b) in test_vectors:
        r = nand_as_and(a, b)
        e = logic_and(a, b)
        print(f"  NAND-AND({a},{b}) = {r}  [{'PASS' if r==e else 'FAIL'}]")

    print("\nNAND as OR:")
    for (a, b) in test_vectors:
        r = nand_as_or(a, b)
        e = logic_or(a, b)
        print(f"  NAND-OR({a},{b}) = {r}  [{'PASS' if r==e else 'FAIL'}]")


def test_universal_nor():
    """Demonstrate NOR universality."""
    print("\n" + "=" * 55)
    print("TEST: NOR Universality")
    print("=" * 55)

    test_vectors = [(0, 0), (0, 1), (1, 0), (1, 1)]

    print("\nNOR as NOT:")
    for a in (0, 1):
        r = nor_as_not(a)
        e = logic_not(a)
        print(f"  NOR-NOT({a}) = {r}  [{'PASS' if r==e else 'FAIL'}]")

    print("\nNOR as OR:")
    for (a, b) in test_vectors:
        r = nor_as_or(a, b)
        e = logic_or(a, b)
        print(f"  NOR-OR({a},{b}) = {r}  [{'PASS' if r==e else 'FAIL'}]")

    print("\nNOR as AND:")
    for (a, b) in test_vectors:
        r = nor_as_and(a, b)
        e = logic_and(a, b)
        print(f"  NOR-AND({a},{b}) = {r}  [{'PASS' if r==e else 'FAIL'}]")


def test_de_morgan():
    """Verify De Morgan's laws."""
    print("\n" + "=" * 55)
    print("TEST: De Morgan's Laws")
    print("=" * 55)

    test_vectors = [(0, 0), (0, 1), (1, 0), (1, 1)]

    print("\nLaw 1: (A.B)' = A' + B'")
    for (a, b) in test_vectors:
        lhs = logic_nand(a, b)
        rhs = logic_or(logic_not(a), logic_not(b))
        ok = "PASS" if lhs == rhs else "FAIL"
        print(f"  ({a}.{b})'={lhs}  vs  {a}'+{b}'={rhs} [{ok}]")

    print("\nLaw 2: (A+B)' = A' . B'")
    for (a, b) in test_vectors:
        lhs = logic_nor(a, b)
        rhs = logic_and(logic_not(a), logic_not(b))
        ok = "PASS" if lhs == rhs else "FAIL"
        print(f"  ({a}+{b})'={lhs}  vs  {a}'.{b}'={rhs} [{ok}]")


if __name__ == "__main__":
    test_basic_gates()
    test_universal_nand()
    test_universal_nor()
    test_de_morgan()
    print("\n" + "=" * 55)
    print("All tests completed.")
    print("=" * 55)
