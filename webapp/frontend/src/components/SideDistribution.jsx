import { useState } from 'react';

// Replaces a 64-bar "spot the tall one" chart. Per-car asymmetry was measured and is
// dominated by car-to-car variation -- 5-9x the fault signal, with only ~4 of 8 cars
// individually pointing at the right side (PLAN.md Phase 10). So a per-channel hotspot
// view would invite an engineer to hunt for a bad wheel that isn't there.
//
// What the verdict actually rests on is the shift between the two sides' distributions,
// so that is what this draws: both spreads on one scale, each side's mean marked, and the
// gap between them measured against how much healthy track varies on its own.
export default function SideDistribution({ channels, predictedSide, asymContext }) {
  const [hover, setHover] = useState(null);

  const vals = channels.map((c) => c.rms);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const pad = (hi - lo) * 0.12 || 0.01;
  const x = (v) => ((v - (lo - pad)) / (hi - lo + 2 * pad)) * 100;

  const sides = ['Side I', 'Side II'].map((side) => {
    const items = channels.filter((c) => c.side === side);
    return { side, items, mean: items.reduce((a, c) => a + c.rms, 0) / items.length };
  });

  const gap = sides[0].mean - sides[1].mean;
  const sd = asymContext?.sd_from_healthy;

  return (
    <div className="gx-dist">
      {sides.map(({ side, items, mean }) => {
        const hot = side === predictedSide;
        const color = hot
          ? (side === 'Side I' ? 'var(--gx-accent)' : 'var(--gx-amber)')
          : 'var(--gx-idle-bar)';
        return (
          <div className="gx-dist-row" key={side}>
            <div className="gx-dist-label">{side}</div>
            <div className="gx-dist-track">
              {items.map((c) => (
                <span
                  key={c.channel}
                  className="gx-dist-dot"
                  style={{ left: `${x(c.rms)}%`, background: color }}
                  onMouseEnter={() => setHover(c)}
                  onMouseLeave={() => setHover(null)}
                />
              ))}
              <span className="gx-dist-mean" style={{ left: `${x(mean)}%`, background: color }} />
              {hover && hover.side === side && (
                <span className="gx-dist-tip" style={{ left: `${x(hover.rms)}%` }}>
                  {hover.channel} · RMS {hover.rms.toFixed(3)}
                </span>
              )}
            </div>
            <div className="gx-dist-mean-val mono">{mean.toFixed(3)}</div>
          </div>
        );
      })}

      <div className="gx-dist-foot">
        <span className="gx-dist-foot-k">Gap between the two side averages</span>
        <span className="mono" style={{ color: 'var(--gx-text)' }}>
          {gap >= 0 ? '+' : ''}{gap.toFixed(3)}
        </span>
        {sd != null && (
          <span>
            — {sd.toFixed(1)}× what healthy track varies by on its own
            {asymContext?.corroborates === false && ' (so the verdict rests on other signals)'}
          </span>
        )}
      </div>
    </div>
  );
}
