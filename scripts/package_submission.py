"""Assemble the submission folder in the layout the PS3 spec requires.

    <Team Name>/
    ├── demo_video.<ext>                 # copied from the repo root if present
    ├── predictions.zip                  # built by validate_submission (schema-checked)
    ├── app/                             # everything needed to run the app
    └── Optional_Items/
        ├── write_up.<ext>               # copied from the repo root if present
        └── <Door|ACV|Rail Corrugation|SHM>/{code/, model/}

    python scripts/package_submission.py --team "<registered team name>"

Nothing from data/ or the organisers' example submission is copied. Missing optional items
are listed at the end rather than failing the build.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

SUBSYSTEMS = {                       # spec folder name -> (package dir, model files)
    "Door": ("subsystems/door", ["model.joblib"]),
    "ACV": ("subsystems/acv", []),
    "Rail Corrugation": ("subsystems/rail_corrugation", ["artifacts/rail_model.joblib",
                                                         "artifacts/train_features.csv"]),
    "SHM": ("subsystems/shm", ["model.joblib", "artifacts/train_features.csv"]),
}
APP_PARTS = ["app", "subsystems", ".streamlit", "requirements.txt", "README.md"]
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.local.joblib", ".DS_Store")


def copytree(src: Path, dst: Path):
    shutil.copytree(src, dst, ignore=IGNORE, dirs_exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", required=True, help="exactly as registered — it names the top-level folder")
    args = ap.parse_args()
    team = DIST / args.team
    if team.exists():
        shutil.rmtree(team)
    team.mkdir(parents=True)
    missing = []

    # 2. predictions.zip — always rebuilt through the validator so nothing malformed ships
    r = subprocess.run([sys.executable, str(ROOT / "scripts/validate_submission.py"), "--zip"],
                       cwd=ROOT, capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print("predictions failed validation — fix them before packaging")
        sys.exit(1)
    shutil.copy2(ROOT / "predictions/predictions.zip", team / "predictions.zip")

    # 3. app — the app plus everything it imports
    app_dst = team / "app"
    for part in APP_PARTS:
        src = ROOT / part
        (copytree if src.is_dir() else shutil.copy2)(src, app_dst / part)
    (app_dst / "RUN.md").write_text(
        "pip install -r requirements.txt\nstreamlit run app/app.py\n\nRun from this folder. "
        "Models are included; no training or raw data is needed.\n")

    # 1. demo video, optional write-up — copied if they exist at the repo root
    videos = [p for p in ROOT.glob("demo_video.*") if p.is_file()]
    if videos:
        shutil.copy2(videos[0], team / videos[0].name)
    else:
        missing.append("demo_video.<mp4|mov> at the repo root (compulsory, <= 3 min)")
    opt = team / "Optional_Items"
    opt.mkdir()
    writeups = [p for p in ROOT.glob("write_up.*") if p.is_file()]
    if writeups:
        shutil.copy2(writeups[0], opt / writeups[0].name)
    else:
        missing.append("write_up.<md|pdf|docx> at the repo root (optional; the PLAN.md files hold the material)")

    # 4.2 dev code and models, one folder per subsystem with the spec's exact names
    for name, (pkg, models) in SUBSYSTEMS.items():
        src = ROOT / pkg
        copytree(src, opt / name / "code")
        for m in models:
            if (opt / name / "code" / m).exists():
                (opt / name / "code" / m).unlink()
        mdir = opt / name / "model"
        mdir.mkdir(parents=True)
        for m in models:
            shutil.copy2(src / m, mdir / Path(m).name)
        if not models:
            (mdir / "NOTE.md").write_text(
                "The ACV ranker has no trained artifact: it is a parameter-free physics rule "
                "(cabin temperature minus cooling setpoint) blended with a fixed-weight heuristic. "
                "See code/PLAN.md.\n")

    print(f"\nbuilt {team.relative_to(ROOT)}/")
    for p in sorted(team.rglob("*")):
        if p.is_file() and "code" not in p.relative_to(team).parts:
            print(f"  {p.relative_to(team)}")
    if missing:
        print("\nstill needed before upload:")
        for m in missing:
            print(f"  - {m}")


if __name__ == "__main__":
    main()
