import { useState } from 'react';
import Banner from '../components/Banner';
import DataTable from '../components/DataTable';
import Dropzone from '../components/Dropzone';
import GapChart from '../components/GapChart';
import Metrics from '../components/Metrics';
import Panel from '../components/Panel';
import Pill from '../components/Pill';
import RankingBars from '../components/RankingBars';
import ReliabilityPanel from '../components/ReliabilityPanel';
import Spinner from '../components/Spinner';
import Verdict from '../components/Verdict';
import { COLORS } from '../theme';
import { downloadCsv } from '../utils/csv';

async function callApi(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export default function AcvPage() {
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
    return callApi('/api/acv/predict', { method: 'POST', body: form });
  });
  const runSample = () => run(() => callApi('/api/acv/sample'));

  const download = () => downloadCsv(
    'acv_predictions.csv', ['file_id', 'ranked_cars'],
    [[result.file_id, result.ranked_cars.join('|')]],
  );

  return (
    <div>
      <h1 className="gx-h1">ACV — refrigerant leak localisation</h1>
      <p className="gx-sub">
        Ranks every car from most to least likely to carry the refrigerant leak.
      </p>

      {!result && (
        <>
          <Banner
            icon="⬆"
            text="Each car is compared with its 7 neighbours: a unit losing refrigerant can't pull its cabin down to the cooling setpoint, and that gap drives the ranking."
          />
          <Dropzone
            label="Drop an ACV telemetry workbook (.xlsx)"
            sub="One train's ACV telemetry for all 8 cars, sampled every 30 s."
            accept=".xlsx"
            onFile={runFile}
            disabled={loading}
          />
          <button className="gx-btn gx-btn-accent" onClick={runSample} disabled={loading}>
            {loading && <Spinner />} {loading ? 'Parsing workbook…' : 'Try the sample — acv_test_case.xlsx'}
          </button>
        </>
      )}

      {error && <div className="gx-alert"><span className="gx-alert-icon">✕</span>{error}</div>}

      {result && (
        <>
          <Banner
            text={`${result.file_id} accepted — ${result.n_cars} cars over ${result.hours.toFixed(1)} h. `
              + `Ranking complete: car ${result.top} most likely faulty.`}
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
              { label: 'Most likely faulty', value: `Car ${result.top}`, note: `blend score ${result.scores[0].score >= 0 ? '+' : ''}${result.scores[0].score.toFixed(2)}`, color: COLORS.red },
              { label: 'Cars evaluated', value: String(result.n_cars), note: 'IDs read from column headers' },
              { label: 'Margin to rank 2', value: result.margin.toFixed(2), note: `car ${result.runner_up} scores ${result.scores[1].score >= 0 ? '+' : ''}${result.scores[1].score.toFixed(2)}` },
              { label: 'Cabin above setpoint', value: result.gap_top === null ? '—' : `${result.gap_top >= 0 ? '+' : ''}${result.gap_top.toFixed(2)} °C`, note: `car ${result.top}, cooling mode`, color: result.gap_top > 0 ? COLORS.red : undefined },
            ]}
          />

          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            <div style={{ flex: '1 1 380px' }}>
              <Panel heading="Ranked cars — most to least likely leak">
                <RankingBars scores={result.scores} />
                <div className="mono" style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--gx-border)', fontSize: 12.5, color: 'var(--gx-faint)', wordBreak: 'break-all' }}>
                  ranked_cars = {result.ranked_cars.join('|')}
                </div>
              </Panel>
            </div>
            <div style={{ flex: '1.15 1 420px' }}>
              {result.chart ? (
                <Panel heading="Cabin temperature vs setpoint, cooling mode"
                       sub="Dashed line is the setpoint. Red is the top-ranked car; the grey band spans the other cars.">
                  <GapChart points={result.chart.points} topCar={result.top} hours={result.hours} />
                </Panel>
              ) : (
                <Panel heading="Cabin temperature vs setpoint">
                  <p className="gx-prose" style={{ color: 'var(--gx-muted)' }}>
                    This workbook carries no cabin-temperature channel, so the ranking comes from
                    the peer-deviation heuristic alone.
                  </p>
                </Panel>
              )}
            </div>
          </div>

          <DataTable
            headers={['rank', 'car', 'score']}
            rows={result.scores.map((s) => [
              s.rank, s.rank === 1 ? <Pill text={`car ${s.car}`} color={COLORS.red} /> : s.car,
              `${s.score >= 0 ? '+' : ''}${s.score.toFixed(2)}`,
            ])}
            title={`acv_predictions.csv · 1 row`}
            schema="file_id, ranked_cars"
            footer="ranked_cars uses each car's ID exactly as it appears in the workbook headers."
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
