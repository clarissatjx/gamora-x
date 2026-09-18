import { useState } from 'react';
import AcvPage from './pages/AcvPage';
import DoorPage from './pages/DoorPage';
import RailPage from './pages/RailPage';
import ShmPage from './pages/ShmPage';

const NAV = [
  { key: 'door', label: 'Door', tag: 'IoU-F1' },
  { key: 'acv', label: 'ACV', tag: 'rank' },
  { key: 'rail', label: 'Rail Corrugation', tag: 'macro-F1' },
  { key: 'shm', label: 'SHM', tag: '1−MAPE' },
];

const PAGES = { door: DoorPage, acv: AcvPage, rail: RailPage, shm: ShmPage };

export default function App() {
  const [view, setView] = useState('rail');
  const Page = PAGES[view];

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <div style={{
        width: 220, flexShrink: 0, borderRight: '1px solid var(--gx-border)',
        padding: '20px 16px', display: 'flex', flexDirection: 'column', gap: 4,
      }}>
        <div className="gx-brand" style={{ marginBottom: 20 }}>
          <div className="gx-mark">g</div>
          <div>
            <div className="gx-name">gamora · CdM</div>
            <div className="mono" style={{ fontSize: 10.5, color: 'var(--gx-faint)' }}>PS3 · React prototype</div>
          </div>
        </div>
        {NAV.map((n) => (
          <button
            key={n.key}
            onClick={() => setView(n.key)}
            className="gx-btn"
            style={{
              justifyContent: 'space-between', display: 'flex', textAlign: 'left',
              background: view === n.key ? 'var(--gx-bg)' : 'transparent',
              borderColor: view === n.key ? 'var(--gx-accent)' : 'var(--gx-border)',
              color: view === n.key ? 'var(--gx-text)' : 'var(--gx-body)',
            }}
          >
            <span>{n.label}</span>
            <span className="mono" style={{ fontSize: 10.5, color: view === n.key ? 'var(--gx-accent)' : 'var(--gx-border-hover)' }}>{n.tag}</span>
          </button>
        ))}
      </div>
      <div style={{ flex: 1, padding: '28px 32px 56px', maxWidth: 1100 }}>
        <div className="gx-crumb" style={{ marginBottom: 18 }}>gamora-x / webapp / {view}</div>
        <Page />
      </div>
    </div>
  );
}
