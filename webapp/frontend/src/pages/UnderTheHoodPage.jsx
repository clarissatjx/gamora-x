import { useEffect, useState } from 'react';
import Glossed from '../components/Glossed';
import Panel from '../components/Panel';
import AsymGauge from '../components/AsymGauge';
import { fetchReliabilityDetail } from '../utils/reliabilityDetail';

const SUBS = [
  {
    key: 'door', name: 'Door', metric: 'IoU-F1', score: '1.000',
    approach: 'Splits the continuous recording into cycles by detecting the gaps between them — '
      + 'this reproduces the official segmentation exactly, so the score reduces to a '
      + 'classification problem. Each cycle is then classified Normal or Abnormal resistance '
      + 'from three current-based features (mid-travel mean current, total current, 75th-'
      + 'percentile current), which separate the two classes almost perfectly. A logistic '
      + 'regression is the primary classifier, with a random forest running alongside as a '
      + 'crosscheck.',
    scoring: 'IoU-F1 credits a predicted cycle by how much its time segment overlaps the true '
      + 'one — getting the timing right matters as much as picking the right cycle.',
  },
  {
    key: 'acv', name: 'ACV', metric: 'rank', score: '1.000',
    approach: 'Not a trained classifier — a physics rule (a car losing refrigerant can’t '
      + 'pull its cabin down to the cooling setpoint) blended with a heuristic score comparing '
      + 'each car against its 7 neighbours across several telemetry categories. Validated by '
      + 'leave-one-case-out on the 6 labelled cases available, the only honest check with that '
      + 'few examples.',
    scoring: 'rank gives partial credit for ranking the true faulty car near the top even when '
      + 'it’s not picked first — full credit for 1st place, less for each rank further down.',
  },
  {
    key: 'rail', name: 'Rail Corrugation', metric: 'macro-F1', score: '0.888',
    approach: 'A gradient-boosted classifier (scikit-learn’s HistGradientBoostingClassifier, '
      + 'class-weighted for the rare fault classes) trained on per-channel vibration and shock '
      + 'features across all 64 axle-box positions.',
    scoring: 'macro-F1 averages each class’s own F1 score equally, regardless of how common '
      + 'that class is — the rare Side I/Side II fault classes count as much as the common '
      + 'Normal class, unlike plain accuracy.',
  },
  {
    key: 'shm', name: 'SHM', metric: '1−MAPE', score: '0.974',
    approach: 'Not a black-box model — counts load cycles with ASTM rainflow counting, then sums '
      + 'each cycle’s damage contribution via a Miner’s-rule sum with a fatigue exponent '
      + 'of 5, recovered from the data rather than supplied by the organisers. A small ridge-'
      + 'regression correction, fit on 7 cycle features and clipped to ±20%, trims the '
      + 'physics-only estimate.',
    scoring: '1−MAPE is one minus the average percentage error of the damage predictions — '
      + '0% error scores 1.0, a 10% average error scores 0.90.',
  },
];

function SubDetail({ s, detail }) {
  return (
    <Panel>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ fontFamily: "'Big Shoulders Display', sans-serif", fontWeight: 700, fontSize: 22 }}>
          {s.name}
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span className="mono" style={{ fontSize: 12, color: 'var(--gx-faint)' }}>{s.metric}</span>
          <span style={{ fontFamily: "'Big Shoulders Display', sans-serif", fontWeight: 700, fontSize: 22, color: 'var(--gx-accent)' }}>
            {s.score}
          </span>
          <span style={{ fontSize: 11, color: 'var(--gx-faint)' }}>held-out</span>
        </div>
      </div>

      <div style={{ marginTop: 14 }}>
        <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--gx-muted)' }}>How it works</div>
        <p className="gx-prose" style={{ marginTop: 4 }}><Glossed text={s.approach} /></p>
      </div>

      <div style={{ marginTop: 14 }}>
        <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--gx-muted)' }}>How it&rsquo;s scored</div>
        <p className="gx-prose" style={{ marginTop: 4 }}><Glossed text={s.scoring} /></p>
      </div>

      {s.key === 'rail' && (
        <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--gx-border)' }}>
          <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--gx-muted)' }}>
            Why one rail is harder to spot than the other
          </div>
          <p className="gx-prose" style={{ marginTop: 4, marginBottom: 14 }}>
            Corrugation on one rail should make that side&rsquo;s axle boxes noisier. Plotting
            that imbalance for every labelled recording shows why that works for one side and
            not the other.
          </p>
          <AsymGauge />
        </div>
      )}

      <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--gx-border)' }}>
        <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--gx-muted)' }}>Reliability, in detail</div>
        {!detail ? (
          <p className="gx-prose" style={{ marginTop: 4, color: 'var(--gx-faint)' }}>Loading…</p>
        ) : (
          <>
            <p className="gx-prose" style={{ marginTop: 4 }}><Glossed text={detail.note} /></p>
            {detail.classes && (
              <ul style={{ margin: '10px 0 0', paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 6 }}>
                {detail.classes.map((c) => (
                  <li key={c.label} className="gx-prose" style={{ color: 'var(--gx-muted)' }}>
                    {c.line} <span className="mono" style={{ color: 'var(--gx-faint)' }}>(n={c.n_true})</span>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </Panel>
  );
}

export default function UnderTheHoodPage() {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchReliabilityDetail().then(setDetail).catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <h1 className="gx-h1">Under the hood</h1>
      <p className="gx-sub">
        How each model actually works and how its score is calculated — the detail behind the
        plain-English verdicts, for whoever wants to dig in.
      </p>

      {error && <div className="gx-alert" style={{ marginTop: 14 }}><span className="gx-alert-icon">✕</span>{error}</div>}

      {SUBS.map((s) => (
        <SubDetail key={s.key} s={s} detail={detail?.[s.key]} />
      ))}
    </div>
  );
}
