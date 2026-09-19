import { useState } from 'react';
import { formatClock, formatDate, formatDuration, parseDoorTs } from '../utils/doorTime';

const STATUS_COLOR = { 'Abnormal resistance': 'var(--gx-red)', Normal: 'var(--gx-green)' };

function CycleTimes({ band, t0 }) {
  const start = parseDoorTs(band.start_time);
  const end = parseDoorTs(band.end_time);
  if (start == null || end == null) {
    return <div className="mono" style={{ fontSize: 11.5, color: 'var(--gx-faint)' }}>{band.start_time} → {band.end_time}</div>;
  }
  const startDate = formatDate(start), endDate = formatDate(end);
  return (
    <>
      <div className="mono" style={{ fontSize: 12 }}>
        {formatClock(start)} → {formatClock(end)}
      </div>
      <div style={{ fontSize: 11.5, color: 'var(--gx-muted)', marginTop: 2 }}>
        lasted {formatDuration(end - start)}
        {t0 != null && start >= t0 && <> · starts {formatDuration(start - t0)} into the recording</>}
      </div>
      <div style={{ fontSize: 11.5, color: 'var(--gx-faint)', marginTop: 2 }}>
        {startDate === endDate ? startDate : `${startDate} → ${endDate}`}
      </div>
    </>
  );
}

// t0: the recording's first timestamp, so each cycle can say how far into the file it sits
// (the x-axis is sample index, which hides the idle gaps between cycles). Older saved results
// don't carry it, so fall back to the first cycle's start.
export default function DoorChart({ trace, bands, t0 }) {
  const [hover, setHover] = useState(null);
  const w = 900, h = 220, pad = 4;
  const n = trace.length;
  if (n < 2) return null;
  const currents = trace.map((t) => t.current);
  const positions = trace.map((t) => t.position);
  const cMin = Math.min(...currents), cMax = Math.max(...currents);
  const pMax = Math.max(...positions, 1) * 3.4;
  const x = (i) => (i / (n - 1)) * (w - 2 * pad) + pad;
  const yC = (v) => h - pad - ((v - cMin) / (cMax - cMin || 1)) * (h - 2 * pad);
  const yP = (v) => h - pad - (v / pMax) * (h - 2 * pad);

  const currentPath = trace.map((t, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${yC(t.current)}`).join(' ');
  const posPath = trace.map((t, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${yP(t.position)}`).join(' ');

  const hovered = hover !== null ? bands[hover] : null;
  const recordingStart = parseDoorTs(t0 ?? bands[0]?.start_time);
  const hoveredMidPct = hovered
    ? ((x(Math.min(hovered.x0, n - 1)) + x(Math.min(hovered.x1, n - 1))) / 2 / w) * 100
    : 0;

  return (
    <div style={{ position: 'relative' }}>
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none">
        {bands.map((b, k) => {
          const bx0 = x(Math.min(b.x0, n - 1));
          const bx1 = x(Math.min(b.x1, n - 1));
          return (
            <rect
              key={k}
              x={bx0}
              y={0}
              width={Math.max(bx1 - bx0, 1)}
              height={h}
              fill={STATUS_COLOR[b.status] || 'var(--gx-green)'}
              stroke={STATUS_COLOR[b.status] || 'var(--gx-green)'}
              strokeOpacity={hover === k ? 0.6 : 0}
              opacity={hover === k ? 0.3 : 0.14}
              style={{ cursor: 'pointer', transition: 'opacity 80ms ease' }}
              onMouseEnter={() => setHover(k)}
              onMouseLeave={() => setHover(null)}
            />
          );
        })}
        <path d={posPath} fill="none" stroke="var(--gx-dim)" strokeWidth="1.3" strokeDasharray="3,3" opacity="0.9" />
        <path d={currentPath} fill="none" stroke="var(--gx-accent)" strokeWidth="1.6" />
      </svg>
      {hovered && (
        <div
          className="gx-chart-tip"
          style={{ left: `${Math.min(Math.max(hoveredMidPct, 12), 88)}%` }}
        >
          <div style={{ fontWeight: 600 }}>Cycle {hovered.n}</div>
          <div style={{ marginBottom: 6, color: STATUS_COLOR[hovered.status] || 'var(--gx-green)' }}>
            {hovered.status} · {(hovered.confidence * 100).toFixed(0)}% confidence
          </div>
          <CycleTimes band={hovered} t0={recordingStart} />
        </div>
      )}
    </div>
  );
}
