import { useState } from 'react';
import AcvPage from './pages/AcvPage';
import DoorPage from './pages/DoorPage';
import RailPage from './pages/RailPage';
import SavedPage from './pages/SavedPage';
import ShmPage from './pages/ShmPage';
import StartPage from './pages/StartPage';
import HistoryPanel from './components/HistoryPanel';
import Term from './components/Term';
import useRunHistory from './hooks/useRunHistory';
import useSavedResults from './hooks/useSavedResults';
import { downloadAcvCsv } from './components/results/AcvResult';
import { downloadDoorCsv } from './components/results/DoorResult';
import { downloadRailCsv } from './components/results/RailResult';
import { downloadShmCsv } from './components/results/ShmResult';

// Scores are the same held-out figures shown throughout the app (README, Streamlit sidebar) —
// static here since they don't depend on any upload.
const NAV = [
  { key: 'door', label: 'Door', tag: 'IoU-F1', score: '1.000', csv: 'door_predictions.csv' },
  { key: 'acv', label: 'ACV', tag: 'rank', score: '1.000', csv: 'acv_predictions.csv' },
  { key: 'rail', label: 'Rail Corrugation', tag: 'macro-F1', score: '0.888', csv: 'rail_predictions.csv' },
  { key: 'shm', label: 'SHM', tag: '1−MAPE', score: '0.974', csv: 'shm_predictions.csv' },
];

const PAGES = { start: StartPage, door: DoorPage, acv: AcvPage, rail: RailPage, shm: ShmPage, saved: SavedPage };
const DOWNLOAD_CSV = { door: downloadDoorCsv, acv: downloadAcvCsv, rail: downloadRailCsv, shm: downloadShmCsv };
const HISTORY_PANEL_WIDTH = 340;

function readSidebarOpen() {
  try {
    return localStorage.getItem('gamora:sidebar-open') !== '0';
  } catch {
    return true;
  }
}

export default function App() {
  const [view, setView] = useState('start');
  const [sidebarOpen, setSidebarOpen] = useState(readSidebarOpen);
  const [historyOpenFor, setHistoryOpenFor] = useState(null);
  const [results, setResults] = useState({ door: null, acv: null, rail: null, shm: null });
  const current = NAV.find((n) => n.key === view);
  const { saved, save, remove, isSaved } = useSavedResults();

  // One history log per subsystem, all owned here — the nav arrow that opens a log and the
  // page that writes to it are siblings, so neither can hold this state on its own.
  const doorHistory = useRunHistory('door');
  const acvHistory = useRunHistory('acv');
  const railHistory = useRunHistory('rail');
  const shmHistory = useRunHistory('shm');
  const HISTORY = { door: doorHistory, acv: acvHistory, rail: railHistory, shm: shmHistory };

  const setResultFor = (key, value) => setResults((prev) => ({ ...prev, [key]: value }));

  const toggleSidebar = () => {
    setSidebarOpen((prev) => {
      const next = !prev;
      try { localStorage.setItem('gamora:sidebar-open', next ? '1' : '0'); } catch { /* ignore */ }
      return next;
    });
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {sidebarOpen ? (
        <div style={{
          width: 268, flexShrink: 0, borderRight: '1px solid var(--gx-border)',
          padding: '20px 14px', display: 'flex', flexDirection: 'column', gap: 4,
        }}>
          <div className="gx-brand" style={{ marginBottom: 22, justifyContent: 'space-between' }}>
            <div className="gx-brand">
              <div className="gx-mark" />
              <div>
                <div className="gx-name">gamora</div>
                <div className="gx-name-sub">Condition monitoring</div>
              </div>
            </div>
            <button className="gx-sidebar-toggle" onClick={toggleSidebar} title="Collapse sidebar" aria-label="Collapse sidebar">
              ‹
            </button>
          </div>

          <button
            onClick={() => setView('start')}
            className={`gx-nav-btn${view === 'start' ? ' active' : ''}`}
          >
            <span className="gx-nav-flag" />
            <span className="gx-nav-label">Get started</span>
          </button>

          <button
            onClick={() => setView('saved')}
            className={`gx-nav-btn${view === 'saved' ? ' active' : ''}`}
          >
            <span className="gx-nav-flag" />
            <span className="gx-nav-label">Saved</span>
            {saved.length > 0 && <span className="gx-nav-tag">{saved.length}</span>}
          </button>

          <div style={{ margin: '12px 2px 6px', fontSize: 11, color: 'var(--gx-dim)', fontWeight: 600 }}>
            Subsystems
          </div>

          {NAV.map((n) => (
            <div key={n.key} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <button
                onClick={() => setView(n.key)}
                className={`gx-nav-btn${view === n.key ? ' active' : ''}`}
                style={{ flex: 1, minWidth: 0 }}
              >
                <span className="gx-nav-flag" />
                <span className="gx-nav-label">{n.label}</span>
                <Term term={n.tag} className="gx-nav-tag">{n.tag}</Term>
              </button>
              <button
                className={`gx-hist-arrow${historyOpenFor === n.key ? ' active' : ''}`}
                onClick={() => setHistoryOpenFor((v) => (v === n.key ? null : n.key))}
                title={`${n.label} run history`}
                aria-label={`${n.label} run history`}
                aria-pressed={historyOpenFor === n.key}
              >
                ›
              </button>
            </div>
          ))}

          {current && (
            <div className="gx-side-meta">
              <div className="gx-side-meta-row">
                <span className="k">held-out score</span>
                <span className="v" style={{ color: 'var(--gx-accent)' }}>{current.score}</span>
              </div>
              <div className="gx-side-meta-row">
                <span className="k">submission file</span>
                <span className="v">{current.csv}</span>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="gx-sidebar-rail">
          <div className="gx-mark" style={{ width: 24, height: 24 }} />
          <button className="gx-sidebar-toggle" onClick={toggleSidebar} title="Open sidebar" aria-label="Open sidebar">
            ›
          </button>
        </div>
      )}

      {/* Slides open right next to the main sidebar — a second, per-subsystem nav rather than
          an overlay, so it doesn't cover the page underneath. */}
      <div
        style={{
          width: historyOpenFor ? HISTORY_PANEL_WIDTH : 0, flexShrink: 0, overflow: 'hidden',
          transition: 'width 200ms ease',
          borderRight: historyOpenFor ? '1px solid var(--gx-border)' : 'none',
          background: 'var(--gx-panel)',
        }}
      >
        {historyOpenFor && (
          <HistoryPanel
            width={HISTORY_PANEL_WIDTH}
            label={NAV.find((n) => n.key === historyOpenFor)?.label}
            history={HISTORY[historyOpenFor].history}
            onClose={() => setHistoryOpenFor(null)}
            onClear={HISTORY[historyOpenFor].clear}
            onView={(entry) => {
              setResultFor(historyOpenFor, entry.result);
              setView(historyOpenFor);
              setHistoryOpenFor(null);
            }}
            onDownload={(entry) => DOWNLOAD_CSV[historyOpenFor](entry.result)}
          />
        )}
      </div>

      <div style={{ flex: 1, padding: '24px 32px 56px', maxWidth: 1148 }}>
        <div className="gx-topbar">
          <div className="gx-status">
            <span className="gx-status-dot" />
            4 of 4 models loaded
          </div>
        </div>
        {/* Every page stays mounted so an uploaded result survives switching tabs — it only
            clears when the page's own logic clears it (new upload, sample run, or Reset). */}
        {Object.entries(PAGES).map(([key, Page]) => (
          <div key={key} style={{ display: view === key ? 'block' : 'none' }}>
            <Page
              onOpen={setView}
              saved={saved} isSaved={isSaved} onSave={save} onRemove={remove}
              result={results[key]} setResult={(v) => setResultFor(key, v)}
              history={HISTORY[key]?.history} onRecord={HISTORY[key]?.record}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
