import { useState } from 'react';
import { tierColor } from '../theme';

// Monitor and Inspect soon share amber (theme.js TIER_COLOR), so the bands differ by strength.
const BAND_OPACITY = { ok: 0.06, monitor: 0.07, inspect: 0.15, act: 0.12 };
const AXIS_TOP = 1.0;

// Running fatigue damage across the recording, shaded by the same urgency tiers the verdict
// uses. No ceiling line: the axis fits the data, and the top tier runs to the top. Plain SVG
// like the other charts; text sits in an HTML overlay because the SVG stretches
// (preserveAspectRatio none) and would distort it. The SVG renders at exactly h px tall, so
// overlay tops are in px.
export default function DamageCurveChart({ curve, nSamples }) {
  const [hover, setHover] = useState(null);
  const { points } = curve;
  const tiers = curve.tiers ?? [];
  const w = 900, h = 220, pad = 4;
  if (points.length < 2) return null;

  const last = points[points.length - 1];
  const xMax = Math.max(last.i, 1);
  // Always runs up to 1.0 (Miner's rule: fatigue life used up) so every file is read on the
  // same scale — no line is drawn there. A file past 1.0 gets a little headroom above its end.
  const yMax = Math.max(AXIS_TOP, last.damage * 1.05);
  const bandTop = (t) => t.to ?? yMax;
  const x = (i) => (i / xMax) * (w - 2 * pad) + pad;
  const y = (v) => h - pad - (v / yMax) * (h - 2 * pad);

  const toPath = (pts) => pts.map((p, k) => `${k === 0 ? 'M' : 'L'} ${x(p.i)} ${y(p.damage)}`).join(' ');
  const pctOf = (i) => ((i / Math.max(nSamples - 1, 1)) * 100).toFixed(1);
  const tierAt = (v) => tiers.find((t) => v >= t.from && (t.to == null || v < t.to));
  // Tiers the curve actually climbed into during this recording (not the one it started in).
  const entries = tiers.filter((t) => t.from > 0 && t.entered_at != null);

  const handleMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const target = (((e.clientX - rect.left) / rect.width) * w - pad) / (w - 2 * pad) * xMax;
    let best = points[0];
    for (const p of points) if (Math.abs(p.i - target) < Math.abs(best.i - target)) best = p;
    setHover(best);
  };

  const hoverTier = hover && tierAt(hover.damage);

  return (
    <div style={{ position: 'relative' }} onMouseMove={handleMove} onMouseLeave={() => setHover(null)}>
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none">
        {tiers.map((t) => (
          <rect
            key={t.tier}
            x={pad} width={w - 2 * pad}
            y={y(bandTop(t))} height={y(t.from) - y(bandTop(t))}
            fill={tierColor(t.tier)} opacity={BAND_OPACITY[t.tier] ?? 0.06}
          />
        ))}
        {tiers.filter((t) => t.from > 0).map((t) => (
          <line key={t.tier} x1={pad} y1={y(t.from)} x2={w - pad} y2={y(t.from)} stroke={tierColor(t.tier)} strokeDasharray="2,4" opacity="0.6" />
        ))}
        <path d={toPath(points)} fill="none" stroke="var(--gx-accent)" strokeWidth="1.8" />
        {hover && (
          <>
            <line x1={x(hover.i)} y1={0} x2={x(hover.i)} y2={h} stroke="var(--gx-border-hover)" strokeDasharray="2,3" />
            <circle cx={x(hover.i)} cy={y(hover.damage)} r="3.5" fill="var(--gx-accent)" />
          </>
        )}
      </svg>

      {tiers.map((t) => (
        <div
          key={t.tier}
          style={{
            position: 'absolute', right: 8, top: (y(t.from) + y(bandTop(t))) / 2 - 8,
            fontSize: 11, color: tierColor(t.tier), pointerEvents: 'none', opacity: 0.95,
          }}
        >
          {t.label}
        </div>
      ))}
      {[0, ...tiers.filter((t) => t.from > 0).map((t) => t.from), AXIS_TOP].map((v) => (
        <div
          key={v}
          className="mono"
          style={{ position: 'absolute', left: 6, top: Math.max(y(v) - 15, 0), fontSize: 10.5, color: 'var(--gx-faint)', pointerEvents: 'none' }}
        >
          {v.toFixed(1)}
        </div>
      ))}

      {hover && (
        <div className="gx-chart-tip" style={{ left: `${Math.min(Math.max((x(hover.i) / w) * 100, 12), 88)}%` }}>
          <div className="mono" style={{ fontSize: 11.5, color: 'var(--gx-faint)' }}>
            sample {hover.i.toLocaleString()} · {pctOf(hover.i)}% through the recording
          </div>
          <div style={{ marginTop: 2 }}>damage so far {hover.damage.toFixed(6)}</div>
          {hoverTier && (
            <div style={{ marginTop: 2, color: tierColor(hoverTier.tier) }}>Level: {hoverTier.label}</div>
          )}
        </div>
      )}

      {entries.length > 0 && (
        <div style={{ fontSize: 12.5, marginTop: 8, color: 'var(--gx-muted)' }}>
          {entries.map((t, k) => (
            <span key={t.tier}>
              {k > 0 && ' · '}
              <span style={{ color: tierColor(t.tier) }}>{t.label}</span> from {pctOf(t.entered_at)}%
            </span>
          ))}
          {' '}of the recording
        </div>
      )}
      <div style={{ fontSize: 12.5, marginTop: 4, color: 'var(--gx-faint)' }}>
        Ends at {last.damage.toFixed(6)}.
      </div>
      {tiers.length > 0 && (
        <div style={{ fontSize: 11.5, marginTop: 4, color: 'var(--gx-faint)' }}>
          Level cut-offs ({tiers.filter((t) => t.from > 0).map((t) => t.from.toFixed(1)).join(' / ')}) are our own
          illustrative thresholds, not an organiser-supplied maintenance limit — the same ones the verdict above uses.
        </div>
      )}
    </div>
  );
}
