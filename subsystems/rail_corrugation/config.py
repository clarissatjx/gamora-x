"""Paths and physical constants for the Rail Corrugation subsystem."""
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The shared layout is data/Rail_Corrugation/ (CLAUDE.md); one local unzip produced an extra
# nested data/data/ level, so accept whichever exists rather than hard-coding either.
_CANDIDATE_DIRS = (
    REPO_ROOT / "data" / "Rail_Corrugation",
    REPO_ROOT / "data" / "data" / "Rail_Corrugation",
)
DATA_DIR = next((p for p in _CANDIDATE_DIRS if p.exists()), _CANDIDATE_DIRS[0])
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
