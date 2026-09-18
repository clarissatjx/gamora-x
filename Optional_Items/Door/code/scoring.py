"""Official Door metric: IoU-weighted F1 (Door_Subsystem_Info_Kit.md, section 4)."""
import pandas as pd

from .loader import parse_ts


def _intervals(df: pd.DataFrame, label_col: str):
    out = []
    for r in df.itertuples(index=False):
        s = parse_ts(getattr(r, "start_time"))
        e = parse_ts(getattr(r, "end_time"))
        out.append((s, e, getattr(r, label_col)))
    return out


def iou_weighted_f1(true_df: pd.DataFrame, pred_df: pd.DataFrame) -> float:
    """true_df: start_time, end_time, status.  pred_df: start_time, end_time, prediction."""
    T = _intervals(true_df, "status")
    P = _intervals(pred_df, "prediction")
    if not T or not P:
        return 0.0

    cands = []
    for i, (ts, te, tl) in enumerate(T):
        for j, (ps, pe, pl) in enumerate(P):
            if tl != pl:
                continue
            inter = max(0.0, (min(te, pe) - max(ts, ps)).total_seconds())
            union = (te - ts).total_seconds() + (pe - ps).total_seconds() - inter
            iou = inter / union if union > 0 else 0.0
            if iou > 0:
                cands.append((iou, i, j))

    cands.sort(key=lambda x: x[0], reverse=True)
    used_t, used_p, total = set(), set(), 0.0
    for iou, i, j in cands:
        if i in used_t or j in used_p:
            continue
        used_t.add(i)
        used_p.add(j)
        total += iou

    recall = total / len(T)
    precision = total / len(P)
    if recall + precision == 0:
        return 0.0
    return 2 * recall * precision / (recall + precision)


if __name__ == "__main__":
    from pathlib import Path
    ans = pd.read_csv(Path(__file__).resolve().parents[2] / "data/Door/Train_Segments_Answer.csv")
    true = ans[["start_time", "end_time", "status"]]

    def as_pred(df, label):
        return pd.DataFrame({"start_time": df.start_time, "end_time": df.end_time, "prediction": label})

    perfect = as_pred(true, true.status)
    flipped = as_pred(true, true.status.map({"Normal": "Abnormal resistance", "Abnormal resistance": "Normal"}))
    all_normal = as_pred(true, "Normal")
    early = perfect.copy()
    early["end_time"] = early.end_time.map(lambda s: (parse_ts(s) - pd.Timedelta(seconds=0.5)).isoformat())

    checks = {
        "perfect": (iou_weighted_f1(true, perfect), 1.0),
        "all labels flipped": (iou_weighted_f1(true, flipped), 0.0),
        "all Normal": (iou_weighted_f1(true, all_normal), 0.7273),
        "ends 0.5s early": (iou_weighted_f1(true, early), 0.8437),
    }
    for name, (got, want) in checks.items():
        status = "OK " if abs(got - want) < 1e-3 else "FAIL"
        print(f"{status} {name:20s} got={got:.4f} want={want}")
    assert all(abs(g - w) < 1e-3 for g, w in checks.values())
