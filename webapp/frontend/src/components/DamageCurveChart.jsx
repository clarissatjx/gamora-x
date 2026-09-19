import { useState } from 'react';

// Running fatigue damage across the recording, with the 1.0 replacement ceiling. Plain SVG like
// the other charts; text sits in an HTML overlay because the SVG stretches (preserveAspectRatio
// none) and would distort it. The SVG renders at exactly h px tall, so overlay tops are in px.
export default function DamageCurveChart({ curve, nSamples }) {
  const [hover, setHover] = useState(null);
  const { points, ceiling, crossed_at: crossedAt } = curve;
  const w = 900, h = 220, pad = 4;
  if (points.length < 2) return null;

  const last = points[points.length - 1];
  const xMax = Math.max(last.i, 1);
  const yMax = Math.max(ceiling, last.damage) * 1.12;
  const x = (i) => (i / xMax) * (w - 2 * pad) + pad;
  const y = (v) => h - pad - (v / yMax) * (h - 2 * pad);

  const toPath = (pts) => pts.map((p, k) => `${k === 0 ? 'M' : 'L'} ${x(p.i)} ${y(p.damage)}`).join(' ');
  const before = crossedAt == null ? points : points.filter((p) => p.i <= crossedAt);
  const after = crossedAt == null ? [] : points.filter((p) => p.i >= crossedAt);
  const area = `${toPath(points)} L ${x(last.i)} ${h - pad} L ${x(0)} ${h - pad} Z`;
  const pctOf = (i) => ((i / Math.max(nSamples - 1, 1)) * 100).toFixed(1);

  const handleMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const target = (((e.clientX - rect.left) / rect.width) * w - pad) / (w - 2 * pad) * xMax;
    let best = points[0];
    for (const p of points) if (Math.abs(p.i - target) < Math.abs(best.i - target)) best = p;
    setHover(best);
  };

  return (
    <div style={{ position: 'relative' }} onMouseMove={handleMove} onMouseLeave={() => setHover(null)}>
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none">
        {[0.25, 0.5, 0.75].map((v) => (
          <line key={v} x1={pad} y1={y(v)} x2={w - pad} y2={y(v)} stroke="var(--gx-grid)" strokeDasharray="2,4" />
        ))}
        <path d={area} fill="var(--gx-accent)" opacity="0.08" />
        <line x1={pad} y1={y(ceiling)} x2={w - pad} y2={y(ceiling)} stroke="var(--gx-red)" strokeWidth="1.4" strokeDasharray="6,4" />
        <path d={toPath(before)} fill="none" stroke="var(--gx-accent)" strokeWidth="1.8" />
        {after.length > 1 && <path d={toPath(after)} fill="none" stroke="var(--gx-red)" strokeWidth="1.8" />}
        {crossedAt != null && (
          <>
            <line x1={x(crossedAt)} y1={0} x2={x(crossedAt)} y2={h} stroke="var(--gx-red)" strokeDasharray="2,3" opacity="0.7" />
            <circle cx={x(crossedAt)} cy={y(ceiling)} r="4.5" fill="var(--gx-red)" />
          </>
        )}
        {hover && (
          <>
            <line x1={x(hover.i)} y1={0} x2={x(hover.i)} y2={h} stroke="var(--gx-border-hover)" strokeDasharray="2,3" />
            <circle cx={x(hover.i)} cy={y(hover.damage)} r="3.5" fill={hover.damage >= ceiling ? 'var(--gx-red)' : 'var(--gx-accent)'} />
          </>
        )}
      </svg>

      <div
        style={{
          position: 'absolute', right: 8, top: y(ceiling) - 20,
          fontSize: 11.5, color: 'var(--gx-red)', fontWeight: 600, pointerEvents: 'none',
        }}
      >
        {ceiling.toFixed(1)} — fatigue life used up · replace
      </div>
      {[0, 0.5].map((v) => (
        <div
          key={v}
          className="mono"
          style={{ position: 'absolute', left: 6, top: y(v) - 15, fontSize: 10.5, color: 'var(--gx-faint)', pointerEvents: 'none' }}
        >
          {v.toFixed(1)}
        </div>
      ))}

      {hover && (
        <div className="gx-chart-tip" style={{ left: `${Math.min(Math.max((x(hover.i) / w) * 100, 12), 88)}%` }}>
          <div className="mono" style={{ fontSize: 11.5, color: 'var(--gx-faint)' }}>
            sample {hover.i.toLocaleString()} · {pctOf(hover.i)}% through the recording
          </div>
          <div style={{ marginTop: 2, color: hover.damage >= ceiling ? 'var(--gx-red)' : 'var(--gx-body)' }}>
            damage so far {hover.damage.toFixed(6)} · {(hover.damage / ceiling * 100).toFixed(1)}% of fatigue life
          </div>
        </div>
      )}

      <div style={{ fontSize: 12.5, marginTop: 8, color: crossedAt != null ? 'var(--gx-red)' : 'var(--gx-faint)' }}>
        {crossedAt != null
          ? `Reached ${ceiling.toFixed(1)} at sample ${crossedAt.toLocaleString()} (${pctOf(crossedAt)}% through the recording) — the fatigue life is used up and the component needs a complete replacement.`
          : `Ends at ${last.damage.toFixed(6)} — ${(ceiling - last.damage).toFixed(6)} below the replacement ceiling of ${ceiling.toFixed(1)}.`}
      </div>
    </div>
  );
}
