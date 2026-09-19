import { useState } from 'react';
import { tierColor } from '../theme';

// Monitor and Inspect soon share amber (theme.js TIER_COLOR), so the bands differ by strength.
const BAND_OPACITY = { ok: 0.06, monitor: 0.07, inspect: 0.15, act: 0.12 };

// Running fatigue damage across the recording, shaded by the same urgency tiers the verdict
// uses, with the 1.0 replacement ceiling. Plain SVG like the other charts; text sits in an HTML
// overlay because the SVG stretches (preserveAspectRatio none) and would distort it. The SVG
// renders at exactly h px tall, so overlay tops are in px.
export default function DamageCurveChart({ curve, nSamples }) {
  const [hover, setHover] = useState(null);
  const { points, ceiling, crossed_at: crossedAt } = curve;
  const tiers = curve.tiers ?? [];
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
  const pctOf = (i) => ((i / Math.max(nSamples - 1, 1)) * 100).toFixed(1);
  const tierAt = (v) => tiers.find((t) => v >= t.from && v < t.to);
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
            y={y(t.to)} height={y(t.from) - y(t.to)}
            fill={tierColor(t.tier)} opacity={BAND_OPACITY[t.tier] ?? 0.06}
          />
        ))}
        {tiers.filter((t) => t.from > 0).map((t) => (
          <line key={t.tier} x1={pad} y1={y(t.from)} x2={w - pad} y2={y(t.from)} stroke={tierColor(t.tier)} strokeDasharray="2,4" opacity="0.6" />
        ))}
        <line x1={pad} y1={y(ceiling)} x2={w - pad} y2={y(ceiling)} stroke="var(--gx-red)" strokeWidth="1.4" strokeDasharray="6,4" />
        <path d={toPath(before)} fill="none" stroke="var(--gx-accent)" strokeWidth="1.8" />
        {after.length > 1 && <path d={toPath(after)} fill="none" stroke="var(--gx-red)" strokeWidth="1.8" />}
        {entries.map((t) => (
          <circle key={t.tier} cx={x(t.entered_at)} cy={y(t.from)} r="4" fill="var(--gx-panel)" stroke={tierColor(t.tier)} strokeWidth="2" />
        ))}
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
      {tiers.map((t) => (
        <div
          key={t.tier}
          style={{
            position: 'absolute', right: 8, top: (y(t.from) + y(t.to)) / 2 - 8,
            fontSize: 11, color: tierColor(t.tier), pointerEvents: 'none', opacity: 0.95,
          }}
        >
          {t.label}
        </div>
      ))}
      {[0, ...tiers.filter((t) => t.from > 0).map((t) => t.from)].map((v) => (
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
          <div style={{ marginTop: 2, color: hover.damage >= ceiling ? 'var(--gx-red)' : hoverTier ? tierColor(hoverTier.tier) : 'var(--gx-body)' }}>
            {hover.damage >= ceiling ? 'Past 1.0 — replace' : hoverTier ? `Level: ${hoverTier.label}` : null}
          </div>
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
      <div style={{ fontSize: 12.5, marginTop: 4, color: crossedAt != null ? 'var(--gx-red)' : 'var(--gx-faint)' }}>
        {crossedAt != null
          ? `Reached ${ceiling.toFixed(1)} at sample ${crossedAt.toLocaleString()} (${pctOf(crossedAt)}% through the recording) — the fatigue life is used up and the component needs a complete replacement.`
          : `Ends at ${last.damage.toFixed(6)} — ${(ceiling - last.damage).toFixed(6)} below the replacement ceiling of ${ceiling.toFixed(1)}.`}
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
