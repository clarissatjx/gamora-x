// Simplification vs the Streamlit version's 8-line overlay: shows the top-ranked car's line
// against a shaded min/max band of the other cars, rather than one line per car.
export default function GapChart({ points }) {
  const w = 900, h = 190, pad = 4;
  const n = points.length;
  if (n < 2) return null;
  const vals = points.flatMap((p) => [p.top, p.others_min, p.others_max]).filter((v) => v !== null && v !== undefined);
  const lo = Math.min(...vals, 0), hi = Math.max(...vals, 0);
  const x = (i) => (i / Math.max(n - 1, 1)) * (w - 2 * pad) + pad;
  const y = (v) => h - pad - ((v - lo) / (hi - lo || 1)) * (h - 2 * pad);

  const upper = points.map((p, i) => (p.others_max === null ? null : `${x(i)},${y(p.others_max)}`)).filter(Boolean);
  const lowerRev = [...points].reverse().map((p, i) => {
    const idx = n - 1 - i;
    return p.others_min === null ? null : `${x(idx)},${y(p.others_min)}`;
  }).filter(Boolean);
  const bandPath = upper.length ? `M ${upper.join(' L ')} L ${lowerRev.join(' L ')} Z` : '';
  const topPath = points
    .map((p, i) => (p.top === null ? null : `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(p.top)}`))
    .filter(Boolean).join(' ');
  const zeroY = y(0);

  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none">
      <line x1={pad} y1={zeroY} x2={w - pad} y2={zeroY} stroke="var(--gx-dim)" strokeDasharray="4,4" />
      {bandPath && <path d={bandPath} fill="var(--gx-border-strong)" opacity="0.5" />}
      <path d={topPath} fill="none" stroke="var(--gx-red)" strokeWidth="2.1" />
    </svg>
  );
}
