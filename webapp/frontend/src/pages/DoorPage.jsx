import { useState } from 'react';
import Banner from '../components/Banner';
import DataTable from '../components/DataTable';
import Dropzone from '../components/Dropzone';
import Metrics from '../components/Metrics';
import Panel from '../components/Panel';
import ReliabilityPanel from '../components/ReliabilityPanel';
import Verdict from '../components/Verdict';
import DoorChart from '../components/DoorChart';
import Glossed from '../components/Glossed';
import Pill from '../components/Pill';
import Spinner from '../components/Spinner';
import { COLORS } from '../theme';
import { downloadCsv } from '../utils/csv';

const ABNORMAL = 'Abnormal resistance';
const STATUS_COLOR = { Normal: COLORS.green, [ABNORMAL]: COLORS.red };

async function callApi(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export default function DoorPage() {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = async (fn) => {
    setLoading(true);
    setError(null);
    try {
      setResult(await fn());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const runFile = (file) => run(async () => {
    const form = new FormData();
    form.append('file', file);
    return callApi('/api/door/predict', { method: 'POST', body: form });
  });
  const runSample = () => run(() => callApi('/api/door/sample'));

  const download = () => downloadCsv(
    'door_predictions.csv',
    ['start_time', 'end_time', 'prediction', 'confidence'],
    result.cycles.map((c) => [c.start_time, c.end_time, c.prediction, c.confidence]),
  );

  return (
    <div>
      <h1 className="gx-h1">Door — cycle detection &amp; classification</h1>
      <p className="gx-sub">
        Continuous stream segmented into door open/close cycles, each classified Normal or
        Abnormal resistance.
      </p>

      {!result && (
        <>
          <Banner
            icon="⬆"
            text="Waiting for a recording. The model finds each open/close cycle on its own — you
              don't need to split the file up. Every cycle it finds is scored, charted and listed
              below, ready to download as a CSV."
          />
          <Dropzone
            label="Drop a door controller recording (.csv)"
            sub="A continuous recording containing many door open/close cycles back to back."
            accept=".csv"
            onFile={runFile}
            disabled={loading}
          />
          <button className="gx-btn gx-btn-accent" onClick={runSample} disabled={loading}>
            {loading && <Spinner />} {loading ? 'Loading…' : 'Try the sample — Test.csv'}
          </button>
        </>
      )}

      {error && <div className="gx-alert"><span className="gx-alert-icon">✕</span>{error}</div>}

      {result && (
        <>
          <Banner
            text={`${result.file_id} accepted — ${result.n_rows.toLocaleString()} rows, ${
              Math.floor(result.duration_s / 60)} min ${(result.duration_s % 60).toFixed(1)} s of stream. ${
              result.n_cycles} cycles detected.`}
          />

          <Verdict
            headline={result.headline}
            tier={result.tier}
            tierLabel={result.tier_label}
            confidenceLabel={result.confidence_label}
            reasoning={result.reasoning}
          />
          <ReliabilityPanel title="How reliable is this?" note={result.reliability_note} />

          <Metrics
            items={[
              { label: 'Cycles detected', value: String(result.n_cycles), note: `in ${(result.duration_s / 60).toFixed(1)} min of stream` },
              { label: 'Abnormal resistance', value: String(result.n_abnormal),
                note: `${((result.n_abnormal / Math.max(result.n_cycles, 1)) * 100).toFixed(1)}% of cycles`,
                color: result.n_abnormal ? COLORS.red : undefined },
              { label: 'Mean cycle length', value: `${result.mean_cycle_length.toFixed(2)} s`, note: 'per cycle' },
              { label: 'Mean confidence', value: result.mean_confidence.toFixed(2), note: `lowest ${result.min_confidence.toFixed(2)}` },
            ]}
          />

          <Panel heading="Motor current with detected door cycles"
                 sub="Shaded bands are detected cycles, cyan is motor current, the dashed grey line is door leaf position.">
            <DoorChart trace={result.chart.trace} bands={result.chart.bands} />
          </Panel>

          {result.evidence && (
            <Panel heading={result.evidence.title}>
              <div className="gx-ev" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 12 }}>
                {result.evidence.tiles.map((t) => (
                  <div key={t.label} style={{ background: 'var(--gx-bg)', border: '1px solid var(--gx-border)', borderRadius: 8, padding: '13px 15px' }}>
                    <div style={{ fontSize: 13, color: 'var(--gx-muted)' }}><Glossed text={t.label} /></div>
                    <div className="mono" style={{ fontSize: 19, fontWeight: 600, margin: '3px 0', color: COLORS.red }}>{t.value}</div>
                    <div className="mono" style={{ fontSize: 12.5, color: 'var(--gx-faint)' }}>{t.note}</div>
                  </div>
                ))}
              </div>
              <p className="gx-prose" style={{ marginTop: 12 }}><Glossed text={result.evidence.prose} /></p>
            </Panel>
          )}

          <DataTable
            headers={['#', 'start_time', 'end_time', 'prediction', 'confidence']}
            rows={result.cycles.map((c) => [
              String(c.n).padStart(2, '0'), c.start_time, c.end_time,
              <Pill text={c.prediction} color={STATUS_COLOR[c.prediction]} />,
              c.confidence.toFixed(2),
            ])}
            title={`door_predictions.csv · ${result.cycles.length} rows`}
            schema="start_time, end_time, prediction"
            footer="confidence is informational — only start_time, end_time and prediction are scored."
          />

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="gx-btn gx-btn-accent" onClick={download}>⬇ Download CSV</button>
            <button className="gx-btn" onClick={() => setResult(null)}>Reset</button>
          </div>
        </>
      )}
    </div>
  );
}
