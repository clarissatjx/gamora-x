import { useState } from 'react';
import Banner from '../components/Banner';
import BatchUploader from '../components/BatchUploader';
import Dropzone from '../components/Dropzone';
import HistoryDrawer from '../components/HistoryDrawer';
import SaveButton from '../components/SaveButton';
import Spinner from '../components/Spinner';
import UploadModeToggle from '../components/UploadModeToggle';
import DoorResult, { downloadDoorCsv } from '../components/results/DoorResult';
import useRunHistory from '../hooks/useRunHistory';
import { buildSavedEntry } from '../utils/savedEntry';

const BATCH_HEADERS = ['file_id', 'start_time', 'end_time', 'prediction', 'confidence'];
const batchRows = (result) => result.cycles.map((c) => [result.file_id, c.start_time, c.end_time, c.prediction, c.confidence]);

async function callApi(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export default function DoorPage({ isSaved, onSave, onRemove }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('single');
  const [historyOpen, setHistoryOpen] = useState(false);
  const { history, record, clear } = useRunHistory('door');

  const run = async (fn) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fn();
      setResult(data);
      record(data);
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

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <div>
          <h1 className="gx-h1">Door — cycle detection &amp; classification</h1>
          <p className="gx-sub">
            Segments a continuous stream into open/close cycles, classifies each Normal or
            Abnormal resistance.
          </p>
        </div>
        <button className="gx-btn" onClick={() => setHistoryOpen(true)}>
          History{history.length > 0 && <span className="gx-nav-tag">{history.length}</span>}
        </button>
      </div>

      {!result && (
        <>
          <Banner
            icon="⬆"
            text="Drop a recording — cycles are found, scored and charted automatically. No need to split the file up first."
          />
          <UploadModeToggle mode={mode} onChange={setMode} />
          {mode === 'single' ? (
            <>
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
          ) : (
            <BatchUploader
              subsystem="door"
              accept=".csv"
              label="Drop multiple door controller recordings (.csv)"
              sub="Each file is segmented and classified independently."
              predictPath="/api/door/predict"
              ResultComponent={DoorResult}
              csvFileName="door_batch_predictions.csv"
              csvHeaders={BATCH_HEADERS}
              buildRows={batchRows}
              isSaved={isSaved}
              onSave={onSave}
              onRemove={onRemove}
              onResult={record}
            />
          )}
        </>
      )}

      {error && <div className="gx-alert"><span className="gx-alert-icon">✕</span>{error}</div>}

      {result && (
        <>
          <DoorResult result={result} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="gx-btn gx-btn-accent" onClick={() => downloadDoorCsv(result)}>⬇ Download CSV</button>
            <SaveButton entry={buildSavedEntry('door', result)} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />
            <button className="gx-btn" onClick={() => setResult(null)}>Reset</button>
          </div>
        </>
      )}

      <HistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        label="Door"
        history={history}
        onClear={clear}
        onView={(entry) => { setResult(entry.result); setHistoryOpen(false); }}
        onDownload={(entry) => downloadDoorCsv(entry.result)}
      />
    </div>
  );
}
