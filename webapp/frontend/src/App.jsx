import { useState } from 'react';
import AcvPage from './pages/AcvPage';
import DoorPage from './pages/DoorPage';
import RailPage from './pages/RailPage';
import SavedPage from './pages/SavedPage';
import ShmPage from './pages/ShmPage';
import StartPage from './pages/StartPage';
import UnderTheHoodPage from './pages/UnderTheHoodPage';
import HistoryPanel from './components/HistoryPanel';
import useRunHistory from './hooks/useRunHistory';
import useSavedResults from './hooks/useSavedResults';
import { downloadAcvCsv } from './components/results/AcvResult';
import { downloadDoorCsv } from './components/results/DoorResult';
import { downloadRailCsv } from './components/results/RailResult';
import { downloadShmCsv } from './components/results/ShmResult';

const NAV = [
  { key: 'door', label: 'Door' },
  { key: 'acv', label: 'ACV' },
  { key: 'rail', label: 'Rail Corrugation' },
  { key: 'shm', label: 'SHM' },
];

const PAGES = {
  start: StartPage, door: DoorPage, acv: AcvPage, rail: RailPage, shm: ShmPage,
  saved: SavedPage, hood: UnderTheHoodPage,
};
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
  const [pendingUpload, setPendingUpload] = useState(null); // { subsystem, file } | null
  const { saved, save, remove, isSaved } = useSavedResults();

  // Lets the Get Started tiles hand a file straight to a subsystem page without owning any
  // upload logic themselves — switch tabs, stash the file, the target page picks it up and
  // clears it once its own runFile has it.
  const handleQuickUpload = (key, file) => {
    setPendingUpload({ subsystem: key, file });
    setView(key);
  };

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
                <div className="gx-name">GAMORA</div>
                <div className="gx-name-sub">Train Condition monitoring</div>
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

          <div style={{ marginTop: 'auto', paddingTop: 14, borderTop: '1px solid var(--gx-border)' }}>
            <button
              onClick={() => setView('hood')}
              className={`gx-nav-btn${view === 'hood' ? ' active' : ''}`}
            >
              <span className="gx-nav-flag" />
              <span className="gx-nav-label">Under the hood</span>
            </button>
          </div>
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
              onUpload={handleQuickUpload}
              saved={saved} isSaved={isSaved} onSave={save} onRemove={remove}
              result={results[key]} setResult={(v) => setResultFor(key, v)}
              history={HISTORY[key]?.history} onRecord={HISTORY[key]?.record}
              pendingFile={pendingUpload?.subsystem === key ? pendingUpload.file : null}
              onConsumePendingFile={() => setPendingUpload(null)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
