import { useState } from 'react';

export default function StressChart({ trace, peaks, mean }) {
  const [hover, setHover] = useState(null);
  const w = 900, h = 200, pad = 4;
  if (trace.length < 2) return null;
  const xs = trace.map((t) => t.i);
  const values = trace.map((t) => t.stress).concat(peaks.map((p) => p.stress));
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...values), yMax = Math.max(...values);
  const x = (i) => ((i - xMin) / (xMax - xMin || 1)) * (w - 2 * pad) + pad;
  const y = (v) => h - pad - ((v - yMin) / (yMax - yMin || 1)) * (h - 2 * pad);
  const path = trace.map((t, i) => `${i === 0 ? 'M' : 'L'} ${x(t.i)} ${y(t.stress)}`).join(' ');

  const handleMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * w;
    const targetI = xMin + ((px - pad) / (w - 2 * pad)) * (xMax - xMin);

    let nearest = trace[0], bestDist = Infinity;
    for (const t of trace) {
      const d = Math.abs(t.i - targetI);
      if (d < bestDist) { bestDist = d; nearest = t; }
    }
    let peak = null, bestPeakDist = 14; // viewBox units — snap to a peak ring under the cursor
    for (const p of peaks) {
      const d = Math.abs(x(p.i) - px);
      if (d < bestPeakDist) { bestPeakDist = d; peak = p; }
    }
    setHover(peak ? { i: peak.i, stress: peak.stress, isPeak: true } : { i: nearest.i, stress: nearest.stress, isPeak: false });
  };

  const hoveredPct = hover ? (x(hover.i) / w) * 100 : 0;

  return (
    <div style={{ position: 'relative' }} onMouseMove={handleMove} onMouseLeave={() => setHover(null)}>
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none">
        <line x1={pad} y1={y(mean)} x2={w - pad} y2={y(mean)} stroke="var(--gx-grid)" strokeDasharray="3,3" />
        <path d={path} fill="none" stroke="var(--gx-accent)" strokeWidth="1" />
        {peaks.map((p, k) => (
          <circle key={k} cx={x(p.i)} cy={y(p.stress)} r="5" fill="transparent" stroke="var(--gx-amber)" strokeWidth="1.6" />
        ))}
        {hover && (
          <>
            <line x1={x(hover.i)} y1={0} x2={x(hover.i)} y2={h} stroke="var(--gx-border-hover)" strokeDasharray="2,3" />
            <circle cx={x(hover.i)} cy={y(hover.stress)} r="3.5" fill={hover.isPeak ? 'var(--gx-amber)' : 'var(--gx-accent)'} />
          </>
        )}
      </svg>
      {hover && (
        <div className="gx-chart-tip" style={{ left: `${Math.min(Math.max(hoveredPct, 10), 90)}%` }}>
          <div className="mono" style={{ fontSize: 11.5, color: 'var(--gx-faint)' }}>sample {hover.i.toLocaleString()}</div>
          <div style={{ marginTop: 2, color: hover.isPeak ? 'var(--gx-amber)' : 'var(--gx-body)' }}>
            stress {hover.stress.toFixed(2)}{hover.isPeak ? ' — peak excursion' : ''}
          </div>
        </div>
      )}
    </div>
  );
}
