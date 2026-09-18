export default function DoorChart({ trace, bands }) {
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

  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none">
      {bands.map((b, k) => (
        <rect
          key={k}
          x={x(Math.min(b.x0, n - 1))}
          y={0}
          width={Math.max(x(Math.min(b.x1, n - 1)) - x(Math.min(b.x0, n - 1)), 1)}
          height={h}
          fill={b.status === 'Abnormal resistance' ? 'var(--gx-red)' : 'var(--gx-green)'}
          opacity={0.14}
        />
      ))}
      <path d={posPath} fill="none" stroke="var(--gx-dim)" strokeWidth="1.3" strokeDasharray="3,3" opacity="0.9" />
      <path d={currentPath} fill="none" stroke="var(--gx-accent)" strokeWidth="1.6" />
    </svg>
  );
}
