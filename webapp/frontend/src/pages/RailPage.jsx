import { useState } from 'react';
import Banner from '../components/Banner';
import DataTable from '../components/DataTable';
import Dropzone from '../components/Dropzone';
import Metrics from '../components/Metrics';
import Panel from '../components/Panel';
import ReliabilityPanel from '../components/ReliabilityPanel';
import Verdict from '../components/Verdict';
import ChannelChart from '../components/ChannelChart';
import { COLORS } from '../theme';

const CLASS_COLOR = { Normal: COLORS.green, 'Side I': COLORS.accent, 'Side II': COLORS.amber };

async function callApi(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export default function RailPage() {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const runFile = async (file) => {
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const data = await callApi('/api/rail/predict', { method: 'POST', body: form });
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const runSample = async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await callApi('/api/rail/sample'));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="gx-h1">Rail Corrugation — 3-class classification</h1>
      <p className="gx-sub">
        One-second axle-box recording classified Normal, Side I or Side II from 64 vibration
        and shock channels.
      </p>
      <div className="gx-footnote">
        Official held-out score <b style={{ color: COLORS.accent }}>0.888</b> vs our own
        cross-validation estimate <b style={{ color: COLORS.text }}>0.81 macro-F1</b> — the two
        are measured on different files and can legitimately disagree; see
        &ldquo;How reliable is this?&rdquo; below.
      </div>

      {!result && (
        <>
          <Banner
            icon="⬆"
            text="Waiting for a recording. Positions 1/3/5/7 sit on the Side I rail and 2/4/6/8 on
              Side II; corrugation shows up as a vibration signature on one side only. A
              stationary train is reported Normal by rule — it cannot generate the excitation."
          />
          <Dropzone
            label="Drop an axle-box recording (.csv)"
            sub="One second at 10 kHz: speed pulse plus 64 axle boxes × vibration and shock."
            accept=".csv"
            onFile={runFile}
          />
          <button className="gx-btn gx-btn-accent" onClick={runSample} disabled={loading}>
            {loading ? 'Loading…' : 'Try the sample — Test33.csv'}
          </button>
        </>
      )}

      {error && <div className="gx-alert">{error}</div>}

      {result && (
        <>
          <Banner
            text={`${result.file_id} accepted — 129 columns, 10 kHz, 1.0 s window. ${
              result.stationary
                ? result.explanation
                : `Classified ${result.csv_prediction} with ${(result.confidence_value * 100).toFixed(0)}% confidence.`
            }`}
            color={result.stationary ? COLORS.dim : CLASS_COLOR[result.csv_prediction]}
            icon={result.stationary ? '?' : (result.csv_prediction !== 'Normal' ? '!' : '✓')}
          />

          <Verdict
            headline={result.headline}
            tier={result.tier}
            tierLabel={result.tier_label}
            confidenceLabel={result.confidence_label}
            reasoning={result.reasoning}
          />
          <ReliabilityPanel
            title="How reliable is this?"
            note={result.reliability.note}
            lines={result.reliability.classes}
          />

          <Metrics
            items={[
              { label: 'Prediction', value: result.prediction,
                note: result.stationary ? 'stationary rule' : 'gradient-boosted classifier',
                color: result.stationary ? COLORS.dim : CLASS_COLOR[result.csv_prediction] },
              { label: 'Confidence', value: result.stationary ? 'rule' : `${(result.confidence_value * 100).toFixed(0)}%`,
                note: result.stationary ? 'no wheel rotation detected' : 'class probability' },
              { label: 'Recording speed', value: `${result.speed_kmh.toFixed(0)} km/h`, note: 'from the pulse channel' },
              { label: 'Side asymmetry', value: `${result.asym >= 0 ? '+' : ''}${result.asym.toFixed(3)}`,
                note: 'Side I − Side II vibration RMS',
                color: result.csv_prediction !== 'Normal' ? CLASS_COLOR[result.csv_prediction] : undefined },
            ]}
          />

          <Panel
            heading="Axle-box vibration energy, 64 channels"
            sub="Per-channel RMS over the 1 s window. Highlighted channels sit on the predicted rail side."
          >
            <ChannelChart channels={result.channels} predictedSide={result.csv_prediction} />
          </Panel>

          <DataTable
            headers={['file_id', 'prediction', 'confidence', 'speed km/h']}
            rows={[[
              result.file_id,
              <span className="pill" style={{ color: CLASS_COLOR[result.csv_prediction],
                background: `color-mix(in srgb, ${CLASS_COLOR[result.csv_prediction]} 12%, transparent)`,
                border: `1px solid color-mix(in srgb, ${CLASS_COLOR[result.csv_prediction]} 30%, transparent)` }}>
                {result.csv_prediction}
              </span>,
              result.stationary ? 'rule' : result.confidence_value.toFixed(2),
              result.speed_kmh.toFixed(0),
            ]]}
            title="rail_predictions.csv · 1 row"
            schema="file_id, prediction"
            footer="only file_id and prediction are submitted; confidence and speed are informational."
          />

          <button className="gx-btn" onClick={() => setResult(null)}>Reset</button>
        </>
      )}
    </div>
  );
}
