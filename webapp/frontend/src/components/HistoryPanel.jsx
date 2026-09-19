import { useState } from 'react';
import Pill from './Pill';
import { tierColor } from '../theme';

function HistoryRow({ entry, onView, onDownload, onRename }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(entry.label || entry.fileId);
  const color = tierColor(entry.tier);
  const when = new Date(entry.ranAt);

  const save = () => {
    const clean = draft.trim();
    if (clean && clean !== (entry.label || entry.fileId)) onRename(entry.id, clean);
    else setDraft(entry.label || entry.fileId);
    setEditing(false);
  };

  return (
    <div className="gx-hist-row">
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="mono" style={{ fontSize: 11.5, color: 'var(--gx-faint)' }}>
          {when.toLocaleDateString()} {when.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
        {editing ? (
          <input
            className="gx-input"
            style={{ marginTop: 4, fontSize: 13.5, fontWeight: 600, padding: '4px 8px' }}
            value={draft}
            autoFocus
            onChange={(e) => setDraft(e.target.value)}
            onFocus={(e) => e.target.select()}
            onBlur={save}
            onKeyDown={(e) => {
              if (e.key === 'Enter') { e.preventDefault(); e.target.blur(); }
              if (e.key === 'Escape') { setDraft(entry.label || entry.fileId); setEditing(false); }
            }}
          />
        ) : (
          <div
            className="gx-hist-name"
            onClick={() => setEditing(true)}
            title="Click to rename"
          >
            {entry.label || entry.fileId}
            <span className="gx-hist-rename-hint">✎</span>
          </div>
        )}
        <div style={{ fontSize: 12.5, color: 'var(--gx-muted)', marginTop: 2 }}>{entry.headline}</div>
        <div style={{ marginTop: 6 }}><Pill text={entry.tierLabel} color={color} /></div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flexShrink: 0 }}>
        <button className="gx-btn" onClick={() => onView(entry)}>View</button>
        <button className="gx-btn" onClick={() => onDownload(entry)}>⬇ CSV</button>
      </div>
    </div>
  );
}

// The "second sidebar" — App.jsx docks this between the main nav and the page content and
// animates its width open/closed; this component just fills whatever width it's given.
export default function HistoryPanel({ width, label, history, onClose, onClear, onView, onDownload, onRename }) {
  return (
    <div style={{ width, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="gx-drawer-head">
        <div>
          <div className="gx-panel-h">{label} runs</div>
          <div style={{ fontSize: 12.5, color: 'var(--gx-faint)', marginTop: 2 }}>
            {history.length} in this browser
          </div>
        </div>
        <button className="gx-btn" onClick={onClose}>Close</button>
      </div>

      <div className="gx-drawer-body">
        {history.length === 0 ? (
          <p className="gx-prose" style={{ color: 'var(--gx-muted)' }}>
            Nothing run yet. Files you upload here — single or batch — will show up in this list.
          </p>
        ) : (
          history.map((entry) => (
            <HistoryRow key={entry.id} entry={entry} onView={onView} onDownload={onDownload} onRename={onRename} />
          ))
        )}
      </div>

      {history.length > 0 && (
        <div className="gx-drawer-foot">
          <button className="gx-btn" onClick={onClear}>Clear history</button>
        </div>
      )}
    </div>
  );
}
