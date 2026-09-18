import { useState } from 'react';
import Banner from '../components/Banner';
import DataTable from '../components/DataTable';
import Dropzone from '../components/Dropzone';
import HistogramChart from '../components/HistogramChart';
import Metrics from '../components/Metrics';
import Panel from '../components/Panel';
import ReliabilityPanel from '../components/ReliabilityPanel';
import Spinner from '../components/Spinner';
import StressChart from '../components/StressChart';
import Verdict from '../components/Verdict';
import { downloadCsv } from '../utils/csv';

async function callApi(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export default function ShmPage() {
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
    return callApi('/api/shm/predict', { method: 'POST', body: form });
  });
  const runSample = () => run(() => callApi('/api/shm/sample'));

  const download = () => downloadCsv(
    'shm_predictions.csv', ['file_id', 'prediction'],
    [[result.file_id, result.damage.toFixed(6)]],
  );

  return (
    <div>
      <h1 className="gx-h1">SHM — cumulative fatigue damage</h1>
      <p className="gx-sub">
        Reduces a dynamic stress series to one cumulative damage value via rainflow counting
        and a calibrated Miner&rsquo;s-rule sum.
      </p>

      {!result && (
        <>
          <Banner
            icon="⬆"
            text="Counts every load cycle with rainflow counting and sums the fatigue contribution — 1.0 means the fatigue life is used up."
          />
          <Dropzone
            label="Drop a dynamic stress segment (.csv, one headerless column)"
            sub="One measurement point's stress time series."
            accept=".csv"
            onFile={runFile}
            disabled={loading}
          />
          <button className="gx-btn gx-btn-accent" onClick={runSample} disabled={loading}>
            {loading && <Spinner />} {loading ? 'Loading…' : 'Try the sample — test02.csv'}
          </button>
        </>
      )}

      {error && <div className="gx-alert"><span className="gx-alert-icon">✕</span>{error}</div>}

      {result && (
        <>
          <Banner
            text={`${result.file_id} accepted — ${result.n_samples.toLocaleString()} samples, ${
              result.n_reversals.toLocaleString()} reversals, ${result.n_cycles.toFixed(0)} rainflow cycles. Damage estimated.`}
          />
          {result.implausible && (
            <div className="gx-alert gx-alert-amber">
              <span className="gx-alert-icon">⚠</span>
              <span>
                {result.file_id}&rsquo;s stress values (peak {result.peak_abs.toFixed(0)}) fall well
                outside the range of our training files (roughly ±20 to ±55). This may not be an SHM
                stress segment — the damage number below could be meaningless for this file.
              </span>
            </div>
          )}

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
              { label: 'Cumulative damage', value: result.damage.toFixed(4), note: 'Palmgren–Miner, dimensionless', color: 'var(--gx-accent)' },
              { label: 'Rainflow cycles', value: result.n_cycles.toLocaleString(undefined, { maximumFractionDigits: 0 }), note: `${result.n_reversals.toLocaleString()} reversals` },
              { label: 'Peak stress range', value: result.max_range.toFixed(1), note: 'largest single cycle' },
              { label: 'Regressor correction', value: result.use_correction ? `×${result.correction_factor.toFixed(3)}` : 'off', note: `analytic ${result.analytic.toFixed(4)}` },
            ]}
          />

          <Panel heading="Dynamic stress time series" sub={`${result.file_id} · ${result.n_samples.toLocaleString()} samples`}>
            <StressChart trace={result.trace} peaks={result.peaks} mean={result.mean} />
            <div style={{ fontSize: 12.5, color: 'var(--gx-faint)', marginTop: 8 }}>
              Amber rings mark the eight largest excursions from the mean — with an S-N exponent
              of 5, a handful of such cycles carries most of the damage.
            </div>
          </Panel>

          <Panel heading="Rainflow cycle histogram" sub="Share of total damage by stress-range bin.">
            <HistogramChart rows={result.histogram} />
          </Panel>

          <DataTable
            headers={['file_id', 'prediction']}
            rows={[[result.file_id, result.damage.toFixed(6)]]}
            title="shm_predictions.csv · 1 row"
            schema="file_id, prediction"
            footer="prediction is the cumulative fatigue damage; 1.0 = fatigue life consumed."
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
