import Banner from '../components/Banner';
import Panel from '../components/Panel';
import Term from '../components/Term';

const SUBS = [
  {
    key: 'door', name: 'Door', tag: 'IoU-F1',
    detects: 'A door cycle drawing more current / less back-EMF than a healthy cycle of the same operation — a sign of added mechanical resistance.',
    input: 'A continuous door-controller recording (.csv). You do not need to cut it into cycles yourself — the model finds each open/close cycle on its own.',
    normal: '"All cycles normal" in green. Nothing to do.',
  },
  {
    key: 'acv', name: 'ACV', tag: 'rank',
    detects: 'Which of a train\'s 8 cars is most likely losing refrigerant, by comparing each car\'s cabin temperature against its 7 neighbours.',
    input: 'One train\'s ACV telemetry workbook (.xlsx), all 8 cars, sampled every 30 s.',
    normal: 'There is no "healthy" case here — every file has exactly one faulty car by design. The ranking is always produced; a low margin/confidence just means the call is less certain.',
  },
  {
    key: 'rail', name: 'Rail Corrugation', tag: 'macro-F1',
    detects: 'Whether a 1-second axle-box vibration recording shows the signature of rail corrugation, and on which side of the track.',
    input: 'A 129-column axle-box recording (.csv): 1 speed-pulse column + 64 axle boxes x vibration/shock, 10 kHz, 1 second.',
    normal: '"No corrugation detected" in green. A stationary recording (train not moving) is reported "Inconclusive," not "Normal" — see the caveats below.',
  },
  {
    key: 'shm', name: 'SHM', tag: '1−MAPE',
    detects: 'How much of a structural component\'s fatigue life has been used up, from a raw dynamic stress time series.',
    input: 'One measurement point\'s stress time series (.csv, single headerless column).',
    normal: 'A damage value near 0 is healthy; near 1.0 means the fatigue life at that point is essentially used up.',
  },
];

export default function StartPage({ onOpen }) {
  return (
    <div>
      <h1 className="gx-h1">Get started</h1>
      <p className="gx-sub">
        New to this tool? This page is for you — what it does, what each subsystem needs, and
        what to check before you act on a result.
      </p>

      <Banner text="This app runs four independent models, one per subsystem. Each takes one raw sensor file and gives back a plain-language verdict — not just a class label or a number — plus how urgent it is and how sure the model actually is." />

      <Panel heading="The four subsystems">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 14 }}>
          {SUBS.map((s) => (
            <div key={s.key} style={{ background: 'var(--gx-bg)', border: '1px solid var(--gx-border)', borderRadius: 8, padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <div style={{ fontWeight: 700, fontSize: 15 }}>{s.name}</div>
                <div className="mono" style={{ fontSize: 10.5, color: 'var(--gx-faint)' }}>{s.tag}</div>
              </div>
              <div style={{ fontSize: 13, color: 'var(--gx-muted)' }}>{s.detects}</div>
              <div style={{ fontSize: 12.5, color: 'var(--gx-faint)', borderTop: '1px solid var(--gx-border)', paddingTop: 8 }}>
                <b style={{ color: 'var(--gx-body)' }}>Needs:</b> {s.input}
              </div>
              <div style={{ fontSize: 12.5, color: 'var(--gx-faint)' }}>
                <b style={{ color: 'var(--gx-body)' }}>Healthy looks like:</b> {s.normal}
              </div>
              <button className="gx-btn gx-btn-accent" onClick={() => onOpen(s.key)} style={{ marginTop: 4 }}>
                Open {s.name} →
              </button>
            </div>
          ))}
        </div>
      </Panel>

      <Panel heading="How to read a result">
        <ol style={{ margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <li className="gx-prose">
            <b>Read the headline first.</b> Every page opens with a plain-English verdict
            ("Side I corrugation detected," not a bare class name) before any chart.
          </li>
          <li className="gx-prose">
            <b>Check the tier and <Term term="confidence">confidence</Term> pills</b> next to the
            headline. The tier (e.g. Monitor / Inspect soon / Inspect before next service) tells
            you how urgently to act; confidence (High/Medium/Low) tells you how much the model
            itself trusts this specific result.
          </li>
          <li className="gx-prose">
            <b>Read "How reliable is this?"</b> right below the verdict — real historical
            recall/precision for this model, not a marketing number. This is what tells you how
            often a result like this one has actually been right before.
          </li>
          <li className="gx-prose">
            <b>Hover any dotted-underlined word</b> (like <Term term="back-EMF">back-EMF</Term> or{' '}
            <Term term="macro-F1">macro-F1</Term>) for a plain-language definition — no need to
            know the domain jargon going in.
          </li>
        </ol>
      </Panel>

      <Panel heading="Before you rely on a result — known caveats">
        <ul style={{ margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <li className="gx-prose">
            Severity tiers (Monitor / Inspect soon / etc.) are a heuristic triage aid this team
            added — there is no organiser-supplied maintenance standard behind the thresholds.
            Always read the reasoning sentence, not just the colour.
          </li>
          <li className="gx-prose">
            A held-out score and a cross-validation score for the same model can legitimately
            disagree (shown explicitly on the Rail page) — they're measured on different files.
          </li>
          <li className="gx-prose">
            A stationary train on Rail Corrugation shows "Inconclusive," not "Normal" — a
            stopped train cannot produce the vibration corrugation causes, so a clean result
            can't be asserted even though that's what gets submitted.
          </li>
          <li className="gx-prose">
            Uploading the wrong file type gets rejected with a specific reason (e.g. "expected
            129 columns, found 3"), never a confident-looking wrong answer.
          </li>
        </ul>
      </Panel>
    </div>
  );
}
