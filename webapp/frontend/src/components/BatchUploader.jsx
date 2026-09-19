import { useState } from 'react';
import Dropzone from './Dropzone';
import Pill from './Pill';
import SaveButton from './SaveButton';
import Spinner from './Spinner';
import { buildSavedEntry } from '../utils/savedEntry';
import { downloadCsv } from '../utils/csv';
import { tierColor } from '../theme';

async function callApi(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

function BatchRow({ item, subsystem, expanded, onToggle, isSaved, onSave, onRemove }) {
  const { file, status, result, error } = item;

  if (status === 'queued' || status === 'running') {
    return (
      <tr>
        <td>{file.name}</td>
        <td colSpan={3} style={{ color: 'var(--gx-faint)' }}>
          {status === 'running' ? <><Spinner /> processing…</> : 'queued'}
        </td>
      </tr>
    );
  }
  if (status === 'error') {
    return (
      <tr>
        <td>{file.name}</td>
        <td colSpan={3} style={{ color: 'var(--gx-red)' }}>{error}</td>
      </tr>
    );
  }

  const color = tierColor(result.tier);
  return (
    <tr>
      <td>{file.name}</td>
      <td>{result.headline}</td>
      <td><Pill text={result.tier_label} color={color} /></td>
      <td style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
        <SaveButton entry={buildSavedEntry(subsystem, result)} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />
        <button className="gx-btn" onClick={onToggle}>{expanded ? 'Hide' : 'View'}</button>
      </td>
    </tr>
  );
}

// Runs several files through the same single-file predict endpoint the live page uses, one at
// a time (a shared backend model instance makes parallel requests a false economy here), and
// gives back a triage table instead of N separate uploads. Expanding a row reuses the same
// <XResult> the single-file flow renders, so nothing about "what a result looks like" is
// duplicated for the batch case.
export default function BatchUploader({
  subsystem, accept, label, sub, predictPath,
  ResultComponent, csvFileName, csvHeaders, buildRows,
  isSaved, onSave, onRemove, onResult,
}) {
  const [items, setItems] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [running, setRunning] = useState(false);

  const runBatch = async (files) => {
    setItems(files.map((file) => ({ file, status: 'queued', result: null, error: null })));
    setExpanded(null);
    setRunning(true);

    for (let i = 0; i < files.length; i++) {
      setItems((prev) => prev.map((it, k) => (k === i ? { ...it, status: 'running' } : it)));
      try {
        const form = new FormData();
        form.append('file', files[i]);
        const result = await callApi(predictPath, { method: 'POST', body: form });
        setItems((prev) => prev.map((it, k) => (k === i ? { ...it, status: 'done', result } : it)));
        onResult?.(result);
      } catch (e) {
        setItems((prev) => prev.map((it, k) => (k === i ? { ...it, status: 'error', error: e.message } : it)));
      }
    }
    setRunning(false);
  };

  if (!items) {
    return (
      <Dropzone label={label} sub={sub} accept={accept} multiple onFile={runBatch} />
    );
  }

  const done = items.filter((it) => it.status === 'done');
  const failed = items.filter((it) => it.status === 'error');

  const downloadAll = () => downloadCsv(csvFileName, csvHeaders, done.flatMap((it) => buildRows(it.result)));
  const saveAll = () => done.forEach((it) => {
    const entry = buildSavedEntry(subsystem, it.result);
    if (!isSaved(entry.id)) onSave(entry);
  });

  return (
    <div>
      <div className="gx-table-wrap">
        <div className="gx-table-head">
          <div className="gx-panel-h">
            Batch — {items.length} file{items.length === 1 ? '' : 's'}
            {running
              ? ' · running…'
              : ` · ${done.length} done${failed.length ? `, ${failed.length} failed` : ''}`}
          </div>
          {!running && done.length > 0 && (
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="gx-btn" onClick={saveAll}>★ Save all</button>
              <button className="gx-btn gx-btn-accent" onClick={downloadAll}>⬇ Download all CSV</button>
            </div>
          )}
        </div>
        <div className="gx-table-scroll">
          <table className="gx">
            <thead><tr><th>file</th><th>result</th><th>tier</th><th /></tr></thead>
            <tbody>
              {items.map((it, i) => (
                <BatchRow
                  key={`${it.file.name}-${i}`}
                  item={it}
                  subsystem={subsystem}
                  expanded={expanded === i}
                  onToggle={() => setExpanded((v) => (v === i ? null : i))}
                  isSaved={isSaved}
                  onSave={onSave}
                  onRemove={onRemove}
                />
              ))}
            </tbody>
          </table>
        </div>
        {!running && (
          <div className="gx-foot">
            <button className="gx-btn" onClick={() => { setItems(null); setExpanded(null); }}>
              Run another batch
            </button>
          </div>
        )}
      </div>

      {expanded !== null && items[expanded]?.result && ResultComponent && (
        <div style={{ marginTop: 14 }}>
          <ResultComponent result={items[expanded].result} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />
        </div>
      )}
    </div>
  );
}
