export default function HistogramChart({ rows }) {
  const maxShare = Math.max(...rows.map((r) => r.share), 0.0001);
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 170 }}>
        {rows.map((r) => (
          <div key={r.bin} style={{ flex: 1, height: '100%', display: 'flex', alignItems: 'flex-end' }}>
            <div
              title={`${r.bin}: ${(r.share * 100).toFixed(1)}% of damage, ${r.cycles.toFixed(0)} cycles`}
              style={{
                width: '100%', height: `${(r.share / maxShare) * 100}%`,
                background: r.hot ? 'var(--gx-amber)' : 'var(--gx-idle-bar)', borderRadius: '2px 2px 0 0',
              }}
            />
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
        {rows.map((r) => (
          <div key={r.bin} className="mono" style={{ flex: 1, fontSize: 9, color: 'var(--gx-faint)', textAlign: 'center' }}>
            {r.bin}
          </div>
        ))}
      </div>
    </div>
  );
}
