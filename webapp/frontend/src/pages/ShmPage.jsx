import { useState } from 'react';
import Banner from '../components/Banner';
import BatchUploader from '../components/BatchUploader';
import Dropzone from '../components/Dropzone';
import SaveButton from '../components/SaveButton';
import Spinner from '../components/Spinner';
import UploadModeToggle from '../components/UploadModeToggle';
import ShmResult from '../components/results/ShmResult';
import { downloadCsv } from '../utils/csv';
import { buildSavedEntry } from '../utils/savedEntry';

const BATCH_HEADERS = ['file_id', 'prediction'];
const batchRows = (result) => [[result.file_id, result.damage.toFixed(6)]];

async function callApi(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export default function ShmPage({ isSaved, onSave, onRemove }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('single');

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
          <UploadModeToggle mode={mode} onChange={setMode} />
          {mode === 'single' ? (
            <>
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
          ) : (
            <BatchUploader
              subsystem="shm"
              accept=".csv"
              label="Drop multiple stress segments (.csv, one headerless column each)"
              sub="Each file's cumulative damage is estimated independently."
              predictPath="/api/shm/predict"
              ResultComponent={ShmResult}
              csvFileName="shm_batch_predictions.csv"
              csvHeaders={BATCH_HEADERS}
              buildRows={batchRows}
              isSaved={isSaved}
              onSave={onSave}
              onRemove={onRemove}
            />
          )}
        </>
      )}

      {error && <div className="gx-alert"><span className="gx-alert-icon">✕</span>{error}</div>}

      {result && (
        <>
          <ShmResult result={result} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="gx-btn gx-btn-accent" onClick={download}>⬇ Download CSV</button>
            <SaveButton entry={buildSavedEntry('shm', result)} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />
            <button className="gx-btn" onClick={() => setResult(null)}>Reset</button>
          </div>
        </>
      )}
    </div>
  );
}
