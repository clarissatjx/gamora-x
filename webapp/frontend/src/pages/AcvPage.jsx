import { useState } from 'react';
import Banner from '../components/Banner';
import BatchUploader from '../components/BatchUploader';
import Dropzone from '../components/Dropzone';
import SaveButton from '../components/SaveButton';
import Spinner from '../components/Spinner';
import UploadModeToggle from '../components/UploadModeToggle';
import AcvResult, { downloadAcvCsv } from '../components/results/AcvResult';
import { buildSavedEntry } from '../utils/savedEntry';

const BATCH_HEADERS = ['file_id', 'ranked_cars'];
const batchRows = (result) => [[result.file_id, result.ranked_cars.join('|')]];

async function callApi(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export default function AcvPage({ isSaved, onSave, onRemove, result, setResult, onRecord }) {
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('single');

  const run = async (fn) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fn();
      setResult(data);
      onRecord(data);
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
          <UploadModeToggle mode={mode} onChange={setMode} />
          {mode === 'single' ? (
            <>
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
          ) : (
            <BatchUploader
              subsystem="acv"
              accept=".xlsx"
              label="Drop multiple ACV telemetry workbooks (.xlsx)"
              sub="Each workbook is ranked independently — one train per file."
              predictPath="/api/acv/predict"
              ResultComponent={AcvResult}
              csvFileName="acv_batch_predictions.csv"
              csvHeaders={BATCH_HEADERS}
              buildRows={batchRows}
              isSaved={isSaved}
              onSave={onSave}
              onRemove={onRemove}
              onResult={onRecord}
            />
          )}
        </>
      )}

      {error && <div className="gx-alert"><span className="gx-alert-icon">✕</span>{error}</div>}

      {result && (
        <>
          <AcvResult result={result} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="gx-btn gx-btn-accent" onClick={() => downloadAcvCsv(result)}>⬇ Download CSV</button>
            <SaveButton entry={buildSavedEntry('acv', result)} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />
            <button className="gx-btn" onClick={() => setResult(null)}>Reset</button>
          </div>
        </>
      )}
    </div>
  );
}
