"""Paths and physical constants for the Rail Corrugation subsystem."""
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Data actually extracted with an extra nested `data/` level (data/data/Rail_Corrugation/...),
# not the data/Rail_Corrugation/ layout CLAUDE.md describes -- confirmed by inspecting the repo.
DATA_DIR = REPO_ROOT / "data" / "data" / "Rail_Corrugation"
TRAIN_DIR = DATA_DIR / "Train"
TEST_DIR = DATA_DIR / "Test"
TRAIN_LABELS_PATH = DATA_DIR / "Train_Labels.csv"

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"

SAMPLE_RATE_HZ = 10_000
N_TEETH = 90
WHEEL_DIAMETER_M = 0.85
WHEEL_CIRCUMFERENCE_M = math.pi * WHEEL_DIAMETER_M

N_CARS = 8
N_POSITIONS = 8
SIDE_I_POSITIONS = (1, 3, 5, 7)
SIDE_II_POSITIONS = (2, 4, 6, 8)

CLASSES = ("Normal", "Side I", "Side II")
