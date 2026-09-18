"""Rainflow cycle counting (ASTM E1049-85, three-point method).

Matches the semantics of the reference `rainflow` PyPI package: cycles closed
in-stream count 1.0, cycles closed against the start of the stack and the
trailing residual count 0.5 each.
"""
import numpy as np


def reversals(x: np.ndarray) -> np.ndarray:
    """Turning points of the series, including both endpoints; flat runs collapse."""
    d = np.diff(x)
    nz = np.nonzero(d)[0]
    if len(nz) == 0:
        return x[[0, -1]]
    s = np.sign(d[nz])
    change = np.nonzero(s[1:] != s[:-1])[0] + 1
    idx = np.concatenate(([0], nz[change], [len(x) - 1]))
    return x[idx]


def count(rev: np.ndarray, residual_weight: float = 0.5):
    """Returns (ranges, means, counts) as float arrays."""
    stack, rng, mean, cnt = [], [], [], []
    for p in rev:
        stack.append(p)
        while len(stack) >= 3:
            x_ = abs(stack[-1] - stack[-2])
            y_ = abs(stack[-2] - stack[-3])
            if x_ < y_:
                break
            if len(stack) == 3:
                rng.append(y_); mean.append((stack[0] + stack[1]) / 2); cnt.append(0.5)
                stack.pop(0)
            else:
                rng.append(y_); mean.append((stack[-2] + stack[-3]) / 2); cnt.append(1.0)
                del stack[-3:-1]
    for i in range(len(stack) - 1):
        rng.append(abs(stack[i + 1] - stack[i]))
        mean.append((stack[i + 1] + stack[i]) / 2)
        cnt.append(residual_weight)
    return np.asarray(rng, float), np.asarray(mean, float), np.asarray(cnt, float)


def cycles(x: np.ndarray, residual_weight: float = 0.5):
    return count(reversals(np.asarray(x, dtype=float)), residual_weight)


if __name__ == "__main__":
    # ASTM E1049 worked example, as documented by the reference package:
    # series [-2, 1, -3, 5, -1, 3, -4, 4, -2] -> (range, count) pairs below.
    series = np.array([-2, 1, -3, 5, -1, 3, -4, 4, -2], float)
    rng, _, cnt = cycles(series)
    got = {}
    for r, c in zip(rng, cnt):
        got[r] = got.get(r, 0.0) + c
    want = {3.0: 0.5, 4.0: 1.5, 6.0: 0.5, 8.0: 1.0, 9.0: 0.5}
    ok = got == want
    print(("OK  " if ok else "FAIL") + f" rainflow reference example -> {sorted(got.items())}")
    assert ok, want
