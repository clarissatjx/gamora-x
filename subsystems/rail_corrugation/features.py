"""Speed derivation + per-file feature extraction for Rail Corrugation.

Column layout of a raw file (129 cols, see Info Kit):
  col 0            : rotating-speed sensor pulse train (raw {0,1} toggle signal, NOT a
                      precomputed speed value -- confirmed by inspecting real data)
  col 1..128       : Car c (1..8) x Position p (1..8) x {vibration, shock}, in that nesting
                      order -- Car1-Pos1-vib, Car1-Pos1-shock, Car1-Pos2-vib, ...

Positions 1/3/5/7 = Side I rail, positions 2/4/6/8 = Side II rail (per Info Kit).
"""
import numpy as np
import pandas as pd
from scipy.stats import kurtosis, skew

from . import config


EXPECTED_COLUMNS = 1 + config.N_CARS * config.N_POSITIONS * 2  # speed pulse + 8 cars x 8 positions x {vib, shock}


def load_raw_file(path):
    """Load one raw CSV as a float32 numpy array, shape (~10000, 129).

    Every downstream feature indexes columns positionally (see `_channel_column_indices`),
    so a file with the wrong column count must fail here with a clear message rather than
    silently producing a classification from misaligned or out-of-range data.
    """
    try:
        df = pd.read_csv(path, dtype=np.float32)
    except pd.errors.EmptyDataError:
        raise ValueError("The file is empty.")
    except (UnicodeDecodeError, ValueError) as e:
        raise ValueError(f"Could not read this as a numeric CSV: {e}")
    if df.shape[1] != EXPECTED_COLUMNS:
        raise ValueError(
            f"Expected {EXPECTED_COLUMNS} columns (1 speed pulse + {config.N_CARS} cars x "
            f"{config.N_POSITIONS} positions x vibration/shock), found {df.shape[1]}. "
            "This doesn't look like a Rail Corrugation axle-box recording."
        )
    if df.isna().any().any():
        raise ValueError("The file has missing or non-numeric values in a data cell.")
    if len(df) < 100:
        raise ValueError(f"Only {len(df)} rows — a 1 s recording at 10 kHz has about 10,000.")
    return df.to_numpy()


def derive_speed_mps(pulse_signal, sample_rate=config.SAMPLE_RATE_HZ,
                      n_teeth=config.N_TEETH,
                      wheel_circumference_m=config.WHEEL_CIRCUMFERENCE_M):
    """Convert the raw {0,1} toothed-wheel pulse train into a speed estimate (m/s).

    Each 0->1 rising edge corresponds to one tooth passing the sensor, so revolutions in
    the window = rising_edge_count / n_teeth. Three independent checks agree:
      - the pulse train's duty cycle is 50.0-50.9% with rising edges exactly equalling
        falling edges, so teeth and gaps are equal width and each tooth yields exactly one
        rising edge (90 per revolution), not two;
      - the Info Kit's "a tooth enters and leaves ... the output toggles" gives two
        transitions per tooth but only one rising edge per tooth;
      - the resulting fleet speeds (mean 37 km/h, max 70 km/h) match metro operation,
        whereas counting every transition would imply a 140 km/h maximum.
    """
    binary = (pulse_signal > 0.5).astype(np.int8)
    rising_edges = int(np.sum((binary[1:] == 1) & (binary[:-1] == 0)))
    window_seconds = len(pulse_signal) / sample_rate
    revolutions = rising_edges / n_teeth
    revolutions_per_second = revolutions / window_seconds
    return revolutions_per_second * wheel_circumference_m


def _channel_time_features(x):
    x = x.astype(np.float64)
    signs = np.sign(x)
    signs[signs == 0] = 1
    zero_crossings = np.sum(signs[1:] != signs[:-1])
    return {
        "rms": float(np.sqrt(np.mean(x ** 2))),
        "std": float(np.std(x)),
        "ptp": float(np.ptp(x)),
        "skew": float(skew(x)),
        "kurtosis": float(kurtosis(x)),
        "zero_cross_rate": float(zero_crossings / len(x)),
    }


def _channel_freq_features(x, sample_rate=config.SAMPLE_RATE_HZ, speed_mps=None):
    x = x.astype(np.float64) - np.mean(x)
    n = len(x)
    spectrum = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)

    # Skip the DC bin when finding the dominant frequency.
    spectrum_ac = spectrum[1:]
    freqs_ac = freqs[1:]
    total_energy = float(np.sum(spectrum_ac ** 2)) + 1e-12

    dominant_idx = int(np.argmax(spectrum_ac))
    dominant_freq = float(freqs_ac[dominant_idx])
    dominant_energy_ratio = float(spectrum_ac[dominant_idx] ** 2 / total_energy)

    spectral_centroid = float(np.sum(freqs_ac * spectrum_ac) / (np.sum(spectrum_ac) + 1e-12))

    out = {
        "dominant_freq": dominant_freq,
        "dominant_energy_ratio": dominant_energy_ratio,
        "spectral_centroid": spectral_centroid,
    }
    # Corrugation is a periodic *wavelength* phenomenon -- wavelength = speed / frequency
    # is (approximately) speed-invariant for a real defect, unlike raw frequency.
    if speed_mps is not None and dominant_freq > 1e-6:
        out["dominant_wavelength_m"] = speed_mps / dominant_freq
    else:
        out["dominant_wavelength_m"] = 0.0
    return out


def extract_channel_features(x, sample_rate=config.SAMPLE_RATE_HZ, speed_mps=None):
    feats = _channel_time_features(x)
    feats.update(_channel_freq_features(x, sample_rate=sample_rate, speed_mps=speed_mps))
    return feats


def _channel_column_indices(positions):
    """Column indices (into the 129-col raw array) for vibration and shock at the given
    axle-box positions, across all 8 cars. Returns (vibration_idx, shock_idx)."""
    vib_idx, shock_idx = [], []
    for car in range(config.N_CARS):
        for pos in positions:
            # col 0 is speed; then for car c (0-based), position p (1-based):
            # base offset = 1 + (c * N_POSITIONS + (p - 1)) * 2
            base = 1 + (car * config.N_POSITIONS + (pos - 1)) * 2
            vib_idx.append(base)
            shock_idx.append(base + 1)
    return vib_idx, shock_idx


SIDE_COLUMN_INDICES = {
    "Side I": _channel_column_indices(config.SIDE_I_POSITIONS),
    "Side II": _channel_column_indices(config.SIDE_II_POSITIONS),
}


def extract_file_features(path):
    """Extract the full per-file feature dict for one raw Rail Corrugation CSV."""
    arr = load_raw_file(path)
    speed_mps = derive_speed_mps(arr[:, 0])

    features = {"speed_mps": speed_mps}

    for side, (vib_idx, shock_idx) in SIDE_COLUMN_INDICES.items():
        side_key = side.replace(" ", "_")
        for signal_name, idx_list in (("vib", vib_idx), ("shock", shock_idx)):
            per_channel = [
                extract_channel_features(arr[:, i], speed_mps=speed_mps)
                for i in idx_list
            ]
            feature_names = per_channel[0].keys()
            for fname in feature_names:
                values = np.array([ch[fname] for ch in per_channel])
                prefix = f"{side_key}_{signal_name}_{fname}"
                features[f"{prefix}_mean"] = float(np.mean(values))
                features[f"{prefix}_max"] = float(np.max(values))
                features[f"{prefix}_std"] = float(np.std(values))

    # Corrugation is defined as an *asymmetry* between the two sides (one side faulty,
    # the other normal) -- direct Side I vs Side II ratio/diff features encode that
    # mechanism directly, rather than leaving the model to infer it from two raw
    # per-side blocks. Spot-checking a few files during EDA showed the sign of
    # (Side I - Side II) tracked the labelled faulty side even when raw per-side
    # magnitudes alone were noisy (both scale with speed).
    side_i_prefix = "Side_I_"
    for key in list(features.keys()):
        if key.startswith(side_i_prefix):
            side_ii_key = "Side_II_" + key[len(side_i_prefix):]
            if side_ii_key in features:
                suffix = key[len(side_i_prefix):]
                a, b = features[key], features[side_ii_key]
                features[f"asym_diff_{suffix}"] = a - b
                features[f"asym_ratio_{suffix}"] = a / (b + 1e-9)

    return features
