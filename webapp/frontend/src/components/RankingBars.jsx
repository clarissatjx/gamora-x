export default function RankingBars({ scores }) {
  const vals = scores.map((s) => s.score);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  return (
    <div>
      {scores.map(({ rank, car, score }) => {
        const pct = hi > lo ? (100 * (score - lo)) / (hi - lo) : 0;
        const color = rank === 1 ? 'var(--gx-red)' : rank <= 3 ? 'var(--gx-accent)' : 'var(--gx-border-strong)';
        return (
          <div key={car} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 9 }}>
            <div className="mono" style={{ fontSize: 12, color: 'var(--gx-faint)', width: 22 }}>
              {String(rank).padStart(2, '0')}
            </div>
            <div className="mono" style={{ fontSize: 14, fontWeight: 600, width: 28 }}>{car}</div>
            <div style={{ flex: 1, height: 22, background: 'var(--gx-bg)', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 4 }} />
            </div>
            <div className="mono" style={{ fontSize: 13, width: 52, textAlign: 'right' }}>
              {score >= 0 ? '+' : ''}{score.toFixed(2)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
