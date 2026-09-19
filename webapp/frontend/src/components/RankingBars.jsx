// Mirrors theme.css's --gx-red / --gx-border-strong as literal RGB so the bar color can be
// interpolated between them (a CSS var can't be blended in JS without a DOM round-trip).
const RED = [232, 89, 95];
const GREY = [58, 69, 82];
function rankColor(t) {
  const [r, g, b] = RED.map((c, i) => Math.round(GREY[i] + (c - GREY[i]) * t));
  return `rgb(${r}, ${g}, ${b})`;
}

// Displays each car's raw model score rescaled to 0-1 within this file (1 = most anomalous of
// the 8 cars, 0 = least) -- display-only rescale, the underlying ranking/model is untouched.
export default function RankingBars({ scores }) {
  const vals = scores.map((s) => s.score);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  return (
    <div>
      {scores.map(({ car, score }) => {
        const t = hi > lo ? (score - lo) / (hi - lo) : 1;
        const color = rankColor(t);
        return (
          <div key={car} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 9 }}>
            <div className="mono" style={{ fontSize: 14, fontWeight: 600, width: 28 }}>{car}</div>
            <div style={{ flex: 1, height: 22, background: 'var(--gx-bg)', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{ width: `${t * 100}%`, height: '100%', background: color, borderRadius: 4 }} />
            </div>
            <div className="mono" style={{ fontSize: 13, width: 34, textAlign: 'right', color: 'var(--gx-text)' }}>
              {t.toFixed(2)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
