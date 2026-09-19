import { useState } from 'react';
import Pill from '../components/Pill';
import AcvResult from '../components/results/AcvResult';
import DoorResult from '../components/results/DoorResult';
import RailResult from '../components/results/RailResult';
import ShmResult from '../components/results/ShmResult';
import { tierColor } from '../theme';

const SUBSYSTEM_LABEL = { door: 'Door', acv: 'ACV', rail: 'Rail Corrugation', shm: 'SHM' };
const RESULT_COMPONENT = { door: DoorResult, acv: AcvResult, rail: RailResult, shm: ShmResult };

function SavedCard({ entry, isSaved, onSave, onRemove, onOpen }) {
  const [open, setOpen] = useState(false);
  const Result = RESULT_COMPONENT[entry.subsystem];
  const color = tierColor(entry.tier);
  const when = new Date(entry.savedAt);

  return (
    <div className="gx-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 220 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="mono" style={{ fontSize: 11.5, color: 'var(--gx-faint)' }}>
              {SUBSYSTEM_LABEL[entry.subsystem] ?? entry.subsystem}
            </span>
            <Pill text={entry.tierLabel} color={color} />
          </div>
          <div style={{ fontFamily: "'Big Shoulders Display', sans-serif", fontWeight: 700, fontSize: 19, marginTop: 4 }}>
            {entry.headline}
          </div>
          <div className="mono" style={{ fontSize: 11.5, color: 'var(--gx-faint)', marginTop: 3 }}>
            {entry.fileId} · saved {when.toLocaleDateString()} {when.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          <button className="gx-btn" onClick={() => onOpen(entry.subsystem)}>Open {SUBSYSTEM_LABEL[entry.subsystem]}</button>
          <button className="gx-btn" onClick={() => setOpen((v) => !v)}>{open ? 'Hide analysis' : 'View analysis'}</button>
          <button className="gx-btn" onClick={() => onRemove(entry.id)}>Remove</button>
        </div>
      </div>
      {open && Result && (
        <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--gx-border)' }}>
          <Result result={entry.result} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />
        </div>
      )}
    </div>
  );
}

export default function SavedPage({ saved, isSaved, onSave, onRemove, onOpen }) {
  return (
    <div>
      <h1 className="gx-h1">Saved</h1>
      <p className="gx-sub">
        Results you&rsquo;ve saved for later — kept in this browser only. Save one from any
        subsystem page once you have a verdict.
      </p>

      {saved.length === 0 ? (
        <div className="gx-panel">
          <p className="gx-prose" style={{ color: 'var(--gx-muted)' }}>
            Nothing saved yet. Run a file on any subsystem, then hit Save on the result.
          </p>
        </div>
      ) : (
        saved.map((entry) => (
          <SavedCard key={entry.id} entry={entry} isSaved={isSaved} onSave={onSave} onRemove={onRemove} onOpen={onOpen} />
        ))
      )}
    </div>
  );
}
