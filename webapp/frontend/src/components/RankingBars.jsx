// Rank col (22) + gap (12) + car-id col (28) + gap (12) before the bar track starts — kept as
// a constant so the shared zero-line below can find the track's horizontal center without
// depending on individual row layout.
const TRACK_OFFSET = 74;
const LABEL_GUTTER = 44; // px reserved at each end of the track so a label never clips the panel edge

// Mirrors theme.css's --gx-red / --gx-border-strong as literal RGB so the bar color can be
// interpolated between them (a CSS var can't be blended in JS without a DOM round-trip).
const RED = [232, 89, 95];
const GREY = [58, 69, 82];
function rankColor(t) {
  const [r, g, b] = RED.map((c, i) => Math.round(GREY[i] + (c - GREY[i]) * t));
  return `rgb(${r}, ${g}, ${b})`;
}

export default function RankingBars({ scores }) {
  const maxAbs = Math.max(...scores.map((s) => Math.abs(s.score)), 0.01);
  const vals = scores.map((s) => s.score);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  return (
    <div style={{ position: 'relative' }}>
      {/* one continuous zero-line running through every row, not a per-row tick */}
      <div style={{
        position: 'absolute', top: 0, bottom: 0,
        left: `calc(50% + ${TRACK_OFFSET / 2}px)`,
        width: 1, background: 'var(--gx-border-strong)',
      }}
      />
      {scores.map(({ rank, car, score }) => {
        const half = Math.min((Math.abs(score) / maxAbs) * 50, 50);
        const positive = score >= 0;
        const color = rankColor(hi > lo ? (score - lo) / (hi - lo) : 1);
        const label = `${score >= 0 ? '+' : ''}${score.toFixed(2)}`;
        return (
          <div key={car} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 9 }}>
            <div className="mono" style={{ fontSize: 12, color: 'var(--gx-faint)', width: 22 }}>
              {String(rank).padStart(2, '0')}
            </div>
            <div className="mono" style={{ fontSize: 14, fontWeight: 600, width: 28 }}>{car}</div>
            <div style={{ flex: 1, position: 'relative', height: 22, background: 'var(--gx-bg)', borderRadius: 4 }}>
              <div style={{
                position: 'absolute', top: 0, bottom: 0, borderRadius: 3, background: color,
                left: positive ? '50%' : `${50 - half}%`,
                width: `${half}%`,
              }}
              />
              <div
                className="mono"
                style={{
                  position: 'absolute', top: '50%', transform: 'translateY(-50%)',
                  fontSize: 11.5, color: 'var(--gx-text)', whiteSpace: 'nowrap',
                  ...(positive
                    ? { left: `min(calc(50% + ${half}% + 6px), calc(100% - ${LABEL_GUTTER}px))` }
                    : { right: `min(calc(50% + ${half}% + 6px), calc(100% - ${LABEL_GUTTER}px))` }),
                }}
              >
                {label}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
