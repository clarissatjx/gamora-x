import { useRef } from 'react';
import Banner from '../components/Banner';
import Panel from '../components/Panel';

const SUBS = [
  {
    key: 'door',
    name: 'Door',
    accept: '.csv',
    detects: 'Flags a cycle drawing more current or less back-EMF than healthy — added mechanical resistance.',
    normal: '"All cycles normal" in green.',
  },
  {
    key: 'acv',
    name: 'ACV',
    accept: '.xlsx',
    detects: 'Ranks which of 8 cars is most likely losing refrigerant, from cabin temperature vs. its neighbours.',
    normal: 'No healthy case — a car is always ranked top. Low margin means less certain, not clean.',
  },
  {
    key: 'rail',
    name: 'Rail Corrugation',
    accept: '.csv',
    detects: 'Flags corrugation in a 1 s axle-box vibration recording, and which rail it’s on.',
    normal: '"No corrugation detected" in green. Stationary trains read "Inconclusive."',
  },
  {
    key: 'shm',
    name: 'SHM',
    accept: '.csv',
    detects: 'Estimates how much fatigue life a structural point has used, from its stress time series.',
    normal: 'Near 0 is healthy. Near 1.0 means fatigue life is used up.',
  },
];

const STEPS = [
  { n: '1', h: 'Pick a subsystem', b: 'Door, ACV, Rail Corrugation, or SHM — whichever file you have.' },
  { n: '2', h: 'Upload a file', b: 'Upload straight from a tile below, or open the subsystem to drop a file or try a sample.' },
  { n: '3', h: 'Read the verdict', b: 'Plain English, with how urgent it is and how sure the model is.' },
];

function SubsystemTile({ s, onOpen, onUpload }) {
  const inputRef = useRef(null);

  return (
    <div className="gx-tile">
      <div className="gx-tile-name">{s.name}</div>
      <div className="gx-tile-detects">{s.detects}</div>
      <div className="gx-tile-need">
        <div><b style={{ color: 'var(--gx-body)' }}>Healthy</b> {s.normal}</div>
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <button className="gx-btn gx-btn-accent" onClick={() => inputRef.current?.click()}>
          Upload {s.accept === '.xlsx' ? 'workbook' : 'CSV'}
        </button>
        <button className="gx-btn" onClick={() => onOpen(s.key)}>Open</button>
        <input
          ref={inputRef}
          type="file"
          accept={s.accept}
          style={{ display: 'none' }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onUpload(s.key, file);
            e.target.value = '';
          }}
        />
      </div>
    </div>
  );
}

export default function StartPage({ onOpen, onUpload }) {
  return (
    <div>
      <h1 className="gx-h1" style={{ marginBottom: 20 }}>Get started</h1>

      <Banner text="Every result comes with how urgent it is, how sure the model is, and why." />

      <Panel>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 20 }}>
          {STEPS.map((s) => (
            <div key={s.n}>
              <div style={{ fontFamily: "'Big Shoulders Display', sans-serif", fontWeight: 700, fontSize: 30, color: 'var(--gx-accent)', lineHeight: 1 }}>
                {s.n}
              </div>
              <div style={{ fontWeight: 600, fontSize: 14.5, marginTop: 6 }}>{s.h}</div>
              <div className="gx-prose" style={{ color: 'var(--gx-muted)', marginTop: 4 }}>{s.b}</div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel heading="Subsystems">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 12, marginTop: 13 }}>
          {SUBS.map((s) => (
            <SubsystemTile key={s.key} s={s} onOpen={onOpen} onUpload={onUpload} />
          ))}
        </div>
      </Panel>
    </div>
  );
}
