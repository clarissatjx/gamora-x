"""Lay the submission out in the shape the PS3 spec requires.

The GitHub repository *is* the submission, so by default this builds in place at the repo
root, which then reads:

    gamora-x/                            (= <Team Name>/)
    ├── demo_video.<ext>                 # recorded by hand; checked for presence and size
    ├── predictions.zip                  # rebuilt through validate_submission.py
    ├── app/                             # the app; runs from the repo root (see app/README.md)
    └── Optional_Items/
        ├── write_up.<ext>               # copied from the repo root if present
        └── <Door|ACV|Rail Corrugation|SHM>/{code/, model/}

    python scripts/package_submission.py             # build in place (tracked)
    python scripts/package_submission.py --dist NAME # additionally build a standalone dist/NAME/

Optional_Items/*/code are copies of subsystems/*, so re-run this after any subsystem change.
Nothing from data/ is ever copied.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITHUB_FILE_LIMIT_MB = 100
VIDEO_WARN_MB = 50

SUBSYSTEMS = {                       # spec folder name -> (package dir, model files)
    "Door": ("subsystems/door", ["model.joblib"]),
    "ACV": ("subsystems/acv", []),
    "Rail Corrugation": ("subsystems/rail_corrugation", ["artifacts/rail_model.joblib",
                                                         "artifacts/train_features.csv"]),
    "SHM": ("subsystems/shm", ["model.joblib", "artifacts/train_features.csv"]),
}
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.local.joblib", ".DS_Store")


def copytree(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=IGNORE)


def build_zip() -> Path:
    r = subprocess.run([sys.executable, str(ROOT / "scripts/validate_submission.py"), "--zip"],
                       cwd=ROOT, capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print("predictions failed validation — fix them before packaging")
        sys.exit(1)
    return ROOT / "predictions.zip"


def build_optional_items(dest: Path):
    opt = dest / "Optional_Items"
    for name, (pkg, models) in SUBSYSTEMS.items():
        src = ROOT / pkg
        code = opt / name / "code"
        copytree(src, code)
        for m in models:
            f = code / m
            if f.exists():
                f.unlink()
        mdir = opt / name / "model"
        if mdir.exists():
            shutil.rmtree(mdir)
        mdir.mkdir(parents=True)
        for m in models:
            shutil.copy2(src / m, mdir / Path(m).name)
        if not models:
            (mdir / "NOTE.md").write_text(
                "The ACV ranker has no trained artifact: it is a parameter-free physics rule "
                "(cabin temperature minus cooling setpoint) blended with a fixed-weight heuristic. "
                "See code/PLAN.md.\n")
    writeups = [p for p in ROOT.glob("write_up.*") if p.is_file()]
    if writeups:
        shutil.copy2(writeups[0], opt / writeups[0].name)
    return bool(writeups)


def check_video():
    videos = [p for p in ROOT.glob("demo_video.*") if p.is_file()]
    if not videos:
        return None, None
    mb = videos[0].stat().st_size / 1e6
    return videos[0], mb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", metavar="TEAM", help="also build a standalone dist/TEAM/ folder for a zip upload")
    args = ap.parse_args()

    zip_path = build_zip()
    has_writeup = build_optional_items(ROOT)
    video, mb = check_video()

    print("\nrepo root now carries the spec's submission tree:")
    for p in ["demo_video", "predictions.zip", "app/", "Optional_Items/"]:
        ok = (video is not None) if p == "demo_video" else (ROOT / p.rstrip("/")).exists()
        print(f"  [{'x' if ok else ' '}] {p}")
    todo = []
    if video is None:
        todo.append("record demo_video.<mp4|mov> (<= 3 min) and put it at the repo root")
    elif mb > GITHUB_FILE_LIMIT_MB:
        todo.append(f"demo_video is {mb:.0f} MB — GitHub rejects files over {GITHUB_FILE_LIMIT_MB} MB; re-encode smaller")
    elif mb > VIDEO_WARN_MB:
        todo.append(f"demo_video is {mb:.0f} MB — fine for GitHub but consider re-encoding under {VIDEO_WARN_MB} MB")
    if not has_writeup:
        todo.append("write write_up.<md|pdf> at the repo root (optional; the PLAN.md files hold the material)")
    todo.append("commit and push so the default branch shows this tree")
    print("\nstill to do:")
    for t in todo:
        print(f"  - {t}")

    if args.dist:
        team = ROOT / "dist" / args.dist
        if team.exists():
            shutil.rmtree(team)
        team.mkdir(parents=True)
        shutil.copy2(zip_path, team / "predictions.zip")
        app_dst = team / "app"
        for part in ["app", "subsystems", ".streamlit", "requirements.txt", "README.md"]:
            src = ROOT / part
            (copytree if src.is_dir() else shutil.copy2)(src, app_dst / part)
        copytree(ROOT / "Optional_Items", team / "Optional_Items")
        if video is not None:
            shutil.copy2(video, team / video.name)
        print(f"\nalso built dist/{args.dist}/ for a folder or zip upload")


if __name__ == "__main__":
    main()
