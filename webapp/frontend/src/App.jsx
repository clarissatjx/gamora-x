import { useState } from 'react';
import AcvPage from './pages/AcvPage';
import DoorPage from './pages/DoorPage';
import RailPage from './pages/RailPage';
import ShmPage from './pages/ShmPage';
import StartPage from './pages/StartPage';
import Term from './components/Term';

// Scores are the same held-out figures shown throughout the app (README, Streamlit sidebar) —
// static here since they don't depend on any upload.
const NAV = [
  { key: 'door', label: 'Door', tag: 'IoU-F1', score: '1.000', csv: 'door_predictions.csv' },
  { key: 'acv', label: 'ACV', tag: 'rank', score: '1.000', csv: 'acv_predictions.csv' },
  { key: 'rail', label: 'Rail Corrugation', tag: 'macro-F1', score: '0.888', csv: 'rail_predictions.csv' },
  { key: 'shm', label: 'SHM', tag: '1−MAPE', score: '0.974', csv: 'shm_predictions.csv' },
];

const PAGES = { start: StartPage, door: DoorPage, acv: AcvPage, rail: RailPage, shm: ShmPage };

export default function App() {
  const [view, setView] = useState('start');
  const Page = PAGES[view];
  const current = NAV.find((n) => n.key === view);

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <div style={{
        width: 246, flexShrink: 0, borderRight: '1px solid var(--gx-border)',
        padding: '20px 14px', display: 'flex', flexDirection: 'column', gap: 4,
      }}>
        <div className="gx-brand" style={{ marginBottom: 20 }}>
          <div className="gx-mark">g</div>
          <div>
            <div className="gx-name">gamora · CdM</div>
            <div className="mono" style={{ fontSize: 10.5, color: 'var(--gx-faint)' }}>PS3 · React prototype</div>
          </div>
        </div>

        <button
          onClick={() => setView('start')}
          className={`gx-nav-btn${view === 'start' ? ' active' : ''}`}
        >
          <span className="gx-nav-dot" />
          <span className="gx-nav-label">Get started</span>
        </button>

        <div style={{ margin: '10px 2px 6px', fontSize: 10.5, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--gx-dim)' }}>
          Subsystems
        </div>

        {NAV.map((n) => (
          <button
            key={n.key}
            onClick={() => setView(n.key)}
            className={`gx-nav-btn${view === n.key ? ' active' : ''}`}
          >
            <span className="gx-nav-dot" />
            <span className="gx-nav-label">{n.label}</span>
            <Term term={n.tag} className="gx-nav-tag">{n.tag}</Term>
          </button>
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

      <div style={{ flex: 1, padding: '24px 32px 56px', maxWidth: 1148 }}>
        <div className="gx-topbar">
          <div className="gx-crumb">gamora-x / webapp / {view}</div>
          <div className="gx-status">
            <span className="gx-status-dot" />
            4 of 4 models loaded
          </div>
        </div>
        <Page onOpen={setView} />
      </div>
    </div>
  );
}
