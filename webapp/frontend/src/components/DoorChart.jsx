import { useState } from 'react';

const STATUS_COLOR = { 'Abnormal resistance': 'var(--gx-red)', Normal: 'var(--gx-green)' };

export default function DoorChart({ trace, bands }) {
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
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Cycle {hovered.n}</div>
          <div className="mono" style={{ fontSize: 11.5, color: 'var(--gx-faint)' }}>
            {hovered.start_time} → {hovered.end_time}
          </div>
          <div style={{ marginTop: 4, color: STATUS_COLOR[hovered.status] || 'var(--gx-green)' }}>
            {hovered.status} · {(hovered.confidence * 100).toFixed(0)}% confidence
          </div>
        </div>
      )}
    </div>
  );
}
