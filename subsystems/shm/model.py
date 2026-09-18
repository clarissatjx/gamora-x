"""Feature set for the SHM damage model.

The reference labels are a Miner's-rule sum over rainflow cycles with S-N exponent 5
(recovered from the training data: the log-log slope against Σ n·σ⁵ is 0.9965 ≈ 1 and the
fit peaks at exactly m = 5). The analytic term is `S5 / C`; the remaining features let a
small ridge model correct residual differences in how the reference count was taken.
"""
import numpy as np

M = 5.0
FEATURES = ["log_S5", "log_S3", "log_S7", "log_max_rng", "log_p99_rng", "log_n_cyc", "mean_stress"]


def miner_sum(rng: np.ndarray, cnt: np.ndarray, m: float = M) -> float:
    return float((cnt * rng ** m).sum())


def cycle_features(rng: np.ndarray, mean: np.ndarray, cnt: np.ndarray) -> dict:
    return {
        "log_S5": np.log(miner_sum(rng, cnt, 5)),
        "log_S3": np.log(miner_sum(rng, cnt, 3)),
        "log_S7": np.log(miner_sum(rng, cnt, 7)),
        "log_max_rng": np.log(rng.max()),
        "log_p99_rng": np.log(np.percentile(rng, 99)),
        "log_n_cyc": np.log(cnt.sum()),
        "mean_stress": float(np.average(mean, weights=cnt)),
    }
