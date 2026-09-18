"""End-to-end holdout score on Train, then a distribution-shift check on Test."""
import numpy as np
import pandas as pd

from .features import featurize
from .loader import load_stream
from .predict import LABELS, load_model, run, to_output
from .scoring import iou_weighted_f1
from .segment import segment
from .train import ANSWERS_CSV, HOLDOUT_TRAIN_N, ROOT, TRAIN_CSV, load_training_set, make_primary

TEST_CSV = ROOT / "data/Door/Test.csv"
UNCERTAIN = (0.2, 0.8)
GAP_AMBIGUOUS = (0.25, 0.75)


def holdout_score():
    df = load_stream(TRAIN_CSV)
    segs = segment(df)
    X, y = load_training_set()
    tr = np.arange(HOLDOUT_TRAIN_N)
    te = np.arange(HOLDOUT_TRAIN_N, len(y))

    model = make_primary().fit(X.iloc[tr], y[tr])
    p = model.predict_proba(X.iloc[te])[:, 1]
    pred_df = to_output(segs.iloc[te], p)

    ans = pd.read_csv(ANSWERS_CSV)
    true_df = ans.iloc[te][["start_time", "end_time", "status"]]
    score = iou_weighted_f1(true_df, pred_df)
    print(f"END-TO-END holdout (train first {HOLDOUT_TRAIN_N}, score last {len(te)} cycles): IoU-weighted F1 = {score:.4f}")
    return score


def drift_check():
    X_tr, y_tr = load_training_set()
    bundle = load_model()
    df = load_stream(TEST_CSV)
    segs, X_te, p, crosscheck = run(df, bundle)
    primary = LABELS[(p >= 0.5).astype(int)]

    print(f"\nTEST: {len(segs)} cycles -> " + ", ".join(f"{k}={v}" for k, v in pd.Series(primary).value_counts().items()))

    # A cycle is ambiguous if its mid-travel current lands in the middle of the gap between the
    # two Train classes; landing slightly past a tight cluster's edge is expected door-to-door drift.
    ambiguous = 0
    for op, name in [(1, "Close"), (0, "Open")]:
        m_tr = X_tr.op.to_numpy() == op
        normal_max = X_tr.cur_mid[m_tr & (y_tr == 0)].max()
        abnormal_min = X_tr.cur_mid[m_tr & (y_tr == 1)].min()
        v_te = X_te.cur_mid[X_te.op.to_numpy() == op]
        rel = (v_te - normal_max) / (abnormal_min - normal_max)
        in_gap = (rel > 0) & (rel < 1)
        amb = in_gap & (rel > GAP_AMBIGUOUS[0]) & (rel < GAP_AMBIGUOUS[1])
        ambiguous += int(amb.sum())
        print(f"  {name}: train Normal<= {normal_max:.0f}, Abnormal>= {abnormal_min:.0f} | "
              f"test in-gap: {int(in_gap.sum())} (max gap position {rel[in_gap].max() if in_gap.any() else 0:.2f}) | ambiguous: {int(amb.sum())}")

    uncertain = int(((p > UNCERTAIN[0]) & (p < UNCERTAIN[1])).sum())
    disagree = int((primary != crosscheck).sum())
    print(f"\nDRIFT CHECK  ambiguous(gap position in {GAP_AMBIGUOUS})={ambiguous}  uncertain(p in {UNCERTAIN})={uncertain}  logreg/rf disagree={disagree}")
    verdict = "SHIP" if ambiguous == uncertain == disagree == 0 else "INSPECT flagged cycles before shipping"
    print(f"VERDICT: {verdict}")

    n_rows = segs.i1 - segs.i0 + 1
    odd = segs[(segs.op == "Open") & (n_rows > 150)]
    for r in odd.itertuples():
        k = segs.index.get_loc(r.Index)
        med = X_tr[X_tr.op == 0].groupby(y_tr[X_tr.op == 0]).median()
        print(f"\nODD cycle seg_id={r.seg_id} ({r.op}, {int(n_rows[r.Index])} rows) start={r.start_str}: "
              f"pred={primary[k]} p_abnormal={p[k]:.3f} rf={crosscheck[k]}")
        cmp = pd.DataFrame({"this": X_te.iloc[k], "train_open_normal_med": med.loc[0], "train_open_abnormal_med": med.loc[1]})
        print(cmp.round(1).to_string())


if __name__ == "__main__":
    holdout_score()
    drift_check()
