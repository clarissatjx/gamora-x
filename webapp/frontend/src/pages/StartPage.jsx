import Banner from '../components/Banner';
import Panel from '../components/Panel';
import Term from '../components/Term';

const SUBS = [
  {
    key: 'door', name: 'Door', tag: 'IoU-F1', score: '1.000',
    detects: 'Flags a cycle drawing more current or less back-EMF than healthy — added mechanical resistance.',
    input: 'Continuous door-controller recording (.csv). Cuts its own cycles.',
    normal: '"All cycles normal" in green.',
  },
  {
    key: 'acv', name: 'ACV', tag: 'rank', score: '1.000',
    detects: 'Ranks which of 8 cars is most likely losing refrigerant, from cabin temperature vs. its neighbours.',
    input: 'ACV telemetry workbook (.xlsx), all 8 cars, 30 s sampling.',
    normal: 'No healthy case — a car is always ranked top. Low margin means less certain, not clean.',
  },
  {
    key: 'rail', name: 'Rail Corrugation', tag: 'macro-F1', score: '0.888',
    detects: 'Flags corrugation in a 1 s axle-box vibration recording, and which rail it’s on.',
    input: 'Axle-box recording (.csv): speed pulse + 64 channels, 10 kHz, 1 s.',
    normal: '"No corrugation detected" in green. Stationary trains read "Inconclusive."',
  },
  {
    key: 'shm', name: 'SHM', tag: '1−MAPE', score: '0.974',
    detects: 'Estimates how much fatigue life a structural point has used, from its stress time series.',
    input: 'One point’s stress time series (.csv, single headerless column).',
    normal: 'Near 0 is healthy. Near 1.0 means fatigue life is used up.',
  },
];

const READ_STEPS = [
  { h: 'Headline first', b: 'Plain English before any chart — "Side I corrugation detected," not a class name.' },
  { h: 'Tier + confidence pills', b: 'Tier is how urgently to act. Confidence is how sure the model is on this file.' },
  { h: 'How reliable is this?', b: 'Real recall/precision for this model, sitting right under the verdict.' },
  { h: 'Dotted underlines', b: 'Hover any jargon term for a plain definition, no lookup needed.' },
];

const CAVEATS = [
  'Severity tiers are our own triage heuristic — no organiser standard sets these thresholds.',
  'Held-out and cross-validation scores can disagree; they’re measured on different files.',
  'Rail Corrugation on a stationary train reads "Inconclusive," never "Normal."',
  'A wrong file type is rejected with a reason — never a confident wrong answer.',
];

export default function StartPage({ onOpen }) {
  return (
    <div>
      <h1 className="gx-h1">Get started</h1>
      <p className="gx-sub">
        Four independent models, one per subsystem — upload a raw sensor file, get a
        plain-language verdict back.
      </p>

      <Banner text="Every result comes with how urgent it is, how sure the model is, and why — not just a class label or a number." />

      <Panel heading="Subsystems">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 12, marginTop: 13 }}>
          {SUBS.map((s) => (
            <button
              key={s.key}
              className="gx-tile"
              onClick={() => onOpen(s.key)}
              style={{ cursor: 'pointer', textAlign: 'left', font: 'inherit', color: 'inherit' }}
            >
              <div className="gx-tile-head">
                <div>
                  <div className="gx-tile-name">{s.name}</div>
                  <Term term={s.tag} className="mono" style={{ fontSize: 11, color: 'var(--gx-faint)' }}>
                    {s.tag}
                  </Term>
                </div>
                <div>
                  <div className="gx-tile-score" style={{ color: 'var(--gx-accent)' }}>{s.score}</div>
                  <div className="gx-tile-score-l">held-out</div>
                </div>
              </div>
              <div className="gx-tile-detects">{s.detects}</div>
              <div className="gx-tile-need">
                <div><b style={{ color: 'var(--gx-body)' }}>Needs</b> {s.input}</div>
                <div style={{ marginTop: 4 }}><b style={{ color: 'var(--gx-body)' }}>Healthy</b> {s.normal}</div>
              </div>
            </button>
          ))}
        </div>
      </Panel>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 14 }}>
        <Panel heading="How to read a result">
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 11 }}>
            {READ_STEPS.map((s) => (
              <div key={s.h}>
                <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--gx-text)' }}>{s.h}</div>
                <div className="gx-prose" style={{ color: 'var(--gx-muted)', marginTop: 2 }}>{s.b}</div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel heading="Known caveats">
          <ul style={{ margin: '12px 0 0', paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 9 }}>
            {CAVEATS.map((c) => (
              <li key={c} className="gx-prose" style={{ color: 'var(--gx-muted)' }}>{c}</li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
