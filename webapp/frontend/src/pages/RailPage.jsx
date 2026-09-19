import { useState } from 'react';
import Banner from '../components/Banner';
import BatchUploader from '../components/BatchUploader';
import Dropzone from '../components/Dropzone';
import HistoryDrawer from '../components/HistoryDrawer';
import SaveButton from '../components/SaveButton';
import Spinner from '../components/Spinner';
import Term from '../components/Term';
import UploadModeToggle from '../components/UploadModeToggle';
import RailResult, { downloadRailCsv } from '../components/results/RailResult';
import useRunHistory from '../hooks/useRunHistory';
import { COLORS } from '../theme';
import { buildSavedEntry } from '../utils/savedEntry';

const BATCH_HEADERS = ['file_id', 'prediction'];
const batchRows = (result) => [[result.file_id, result.csv_prediction]];

async function callApi(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export default function RailPage({ isSaved, onSave, onRemove }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('single');
  const [historyOpen, setHistoryOpen] = useState(false);
  const { history, record, clear } = useRunHistory('rail');

  const runFile = async (file) => {
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const data = await callApi('/api/rail/predict', { method: 'POST', body: form });
      setResult(data);
      record(data);
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
      const data = await callApi('/api/rail/sample');
      setResult(data);
      record(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <div>
          <h1 className="gx-h1">Rail Corrugation — 3-class classification</h1>
          <p className="gx-sub">
            Classifies a one-second axle-box recording Normal, Side I or Side II from 64
            vibration and shock channels.
          </p>
        </div>
        <button className="gx-btn" onClick={() => setHistoryOpen(true)}>
          History{history.length > 0 && <span className="gx-nav-tag">{history.length}</span>}
        </button>
      </div>
      <div className="gx-footnote">
        Official <Term term="held-out">held-out</Term> score <b style={{ color: COLORS.accent }}>0.888</b> vs our own
        <Term term="cross-validation"> cross-validation</Term> estimate <b style={{ color: COLORS.text }}>0.81 <Term term="macro-F1">macro-F1</Term></b> — measured
        on different files, so the two can disagree; see &ldquo;How reliable is this?&rdquo; below.
      </div>

      {!result && (
        <>
          <Banner
            icon="⬆"
            text="Positions 1/3/5/7 sit on the Side I rail, 2/4/6/8 on Side II — corrugation shows up as a vibration signature on one side only. A stationary train can't generate that signature, so this app reads it Inconclusive (the submitted label is still Normal)."
          />
          <UploadModeToggle mode={mode} onChange={setMode} />
          {mode === 'single' ? (
            <>
              <Dropzone
                label="Drop an axle-box recording (.csv)"
                sub="One second at 10 kHz: speed pulse plus 64 axle boxes × vibration and shock."
                accept=".csv"
                onFile={runFile}
                disabled={loading}
              />
              <button className="gx-btn gx-btn-accent" onClick={runSample} disabled={loading}>
                {loading && <Spinner />} {loading ? 'Loading…' : 'Try the sample — Test33.csv'}
              </button>
            </>
          ) : (
            <BatchUploader
              subsystem="rail"
              accept=".csv"
              label="Drop multiple axle-box recordings (.csv)"
              sub="Each 1 s recording is classified independently."
              predictPath="/api/rail/predict"
              ResultComponent={RailResult}
              csvFileName="rail_batch_predictions.csv"
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
          <RailResult result={result} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="gx-btn gx-btn-accent" onClick={() => downloadRailCsv(result)}>⬇ Download CSV</button>
            <SaveButton entry={buildSavedEntry('rail', result)} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />
            <button className="gx-btn" onClick={() => setResult(null)}>Reset</button>
          </div>
        </>
      )}

      <HistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        label="Rail Corrugation"
        history={history}
        onClear={clear}
        onView={(entry) => { setResult(entry.result); setHistoryOpen(false); }}
        onDownload={(entry) => downloadRailCsv(entry.result)}
      />
    </div>
  );
}
