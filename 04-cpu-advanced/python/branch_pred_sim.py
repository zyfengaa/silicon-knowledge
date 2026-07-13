"""
branch_pred_sim.py — Branch predictor simulator.

Simulates three branch prediction strategies on a given branch history
string and reports accuracy for each:

  - Always Taken:            always predicts T (taken)
  - Always Not-Taken:        always predicts N (not taken)
  - 2-bit Saturating Counter: 4-state saturating counter per branch

Usage:
    python branch_pred_sim.py [--history "TTTTNTNTTTN..."]

If no --history string is provided, a default pattern is used.
"""

import argparse


# -----------------------------------------------------------------------
#  Predictors
# -----------------------------------------------------------------------

class AlwaysTaken:
    """Predict 'taken' for every branch."""
    def predict(self, _pc: int) -> str:
        return "T"

    def update(self, _pc: int, _actual: str) -> None:
        pass

    def __str__(self) -> str:
        return "Always Taken"


class AlwaysNotTaken:
    """Predict 'not-taken' for every branch."""
    def predict(self, _pc: int) -> str:
        return "N"

    def update(self, _pc: int, _actual: str) -> None:
        pass

    def __str__(self) -> str:
        return "Always Not-Taken"


class Saturating2Bit:
    """
    Per-address 2-bit saturating counter.

    State encoding:
        0b00  ->  strong not-taken  (predict N)
        0b01  ->  weak not-taken    (predict N)
        0b10  ->  weak taken        (predict T)
        0b11  ->  strong taken      (predict T)

    Update rule (saturating):
        actual == T  ->  state = min(state + 1, 3)
        actual == N  ->  state = max(state - 1, 0)
    """

    def __init__(self) -> None:
        self._table: dict[int, int] = {}     # pc -> 2-bit state

    def predict(self, pc: int) -> str:
        state = self._table.get(pc, 0b01)     # default: weak not-taken
        return "T" if state >= 0b10 else "N"

    def update(self, pc: int, actual: str) -> None:
        state = self._table.get(pc, 0b01)
        if actual == "T":
            state = min(state + 1, 3)
        else:  # "N"
            state = max(state - 1, 0)
        self._table[pc] = state

    def __str__(self) -> str:
        return "2-bit Saturating Counter"


# -----------------------------------------------------------------------
#  Simulation
# -----------------------------------------------------------------------

def simulate(predictor, history: str) -> tuple[int, int]:
    """
    Run the predictor against the full history string.

    Returns (correct_count, total_count).
    """
    correct = 0
    for idx, actual in enumerate(history):
        pred = predictor.predict(idx)        # use index as pseudo-PC
        if pred == actual:
            correct += 1
        predictor.update(idx, actual)
    return correct, len(history)


# -----------------------------------------------------------------------
#  Main
# -----------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Branch predictor simulator"
    )
    parser.add_argument(
        "--history", type=str, default=None,
        help="Branch history string of T (taken) and N (not-taken) "
             "characters, e.g. TTTTNTNTTTN. "
             "If omitted a built-in pattern is used."
    )
    args = parser.parse_args()

    history = args.history
    if history is None:
        # A moderately tricky pattern: long runs with a few reversals.
        history = (
            "T" * 8 + "N" * 2 +          # 8 taken, 2 not-taken
            "T" * 6 + "N" * 4 +          # 6 taken, 4 not-taken
            "T" * 10 + "N" * 1 +         # 10 taken, 1 not-taken
            "T" * 4 + "N" * 4 +          # alternating-ish
            "TNTNTNTN" +                 # strict alternation
            "T" * 12 + "N" * 2 +         # long taken run
            "N" * 5 + "T" * 3 +          # reversal pattern
            "T" * 8 + "N" * 3
        )

    print("Branch History String:")
    print(f"  {history}")
    print(f"  Length: {len(history)}")
    print(f"  Taken proportion: {history.count('T') / len(history) * 100:.1f}%")
    print()

    # Run each predictor.
    predictors = [
        AlwaysTaken(),
        AlwaysNotTaken(),
        Saturating2Bit(),
    ]

    print(f"{'Predictor':<30} {'Correct':>7} {'Total':>7} {'Accuracy':>10}")
    print("-" * 55)
    for pred in predictors:
        correct, total = simulate(pred, history)
        acc = correct / total * 100.0
        print(f"{str(pred):<30} {correct:>7} {total:>7} {acc:>9.2f}%")


if __name__ == "__main__":
    main()

# References:
#   - Hennessy, J. L. & Patterson, D. A. "Computer Architecture:
#     A Quantitative Approach", 6th Edition, Chapter 3 (Branch Prediction).
#   - Yeh, T. Y. & Patt, Y. N. "Alternative Implementations of
#     Two-Level Adaptive Branch Prediction." ISCA, 1992.
#   - Seznec, A. "TAGE-SC-L Branch Predictors." JILP, 2014.
#   - Seznec, A. & Michaud, P. "A Case for (Partially) Tagged Geometric
#     History Length Branch Prediction." JILP, 2006.

