export default function StressChart({ trace, peaks, mean }) {
  const w = 900, h = 200, pad = 4;
  if (trace.length < 2) return null;
  const xs = trace.map((t) => t.i);
  const values = trace.map((t) => t.stress).concat(peaks.map((p) => p.stress));
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...values), yMax = Math.max(...values);
  const x = (i) => ((i - xMin) / (xMax - xMin || 1)) * (w - 2 * pad) + pad;
  const y = (v) => h - pad - ((v - yMin) / (yMax - yMin || 1)) * (h - 2 * pad);
  const path = trace.map((t, i) => `${i === 0 ? 'M' : 'L'} ${x(t.i)} ${y(t.stress)}`).join(' ');

  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none">
      <line x1={pad} y1={y(mean)} x2={w - pad} y2={y(mean)} stroke="var(--gx-grid)" strokeDasharray="3,3" />
      <path d={path} fill="none" stroke="var(--gx-accent)" strokeWidth="1" />
      {peaks.map((p, k) => (
        <circle key={k} cx={x(p.i)} cy={y(p.stress)} r="5" fill="transparent" stroke="var(--gx-amber)" strokeWidth="1.6" />
      ))}
    </svg>
  );
}
