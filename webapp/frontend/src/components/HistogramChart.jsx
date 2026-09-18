import { useState } from 'react';

export default function HistogramChart({ rows }) {
  const [hover, setHover] = useState(null);
  const maxShare = Math.max(...rows.map((r) => r.share), 0.0001);
  const n = rows.length;
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 170 }}>
        {rows.map((r, k) => {
          const edge = k < n * 0.15 ? 'left' : k > n * 0.85 ? 'right' : 'center';
          const tipStyle = edge === 'left' ? { left: 0, transform: 'none' }
            : edge === 'right' ? { left: 'auto', right: 0, transform: 'none' }
            : undefined;
          return (
            <div
              key={r.bin}
              className="gx-bar-wrap"
              onMouseEnter={() => setHover(k)}
              onMouseLeave={() => setHover(null)}
            >
              <div
                style={{
                  width: '100%', height: `${(r.share / maxShare) * 100}%`,
                  background: r.hot ? 'var(--gx-amber)' : hover === k ? 'var(--gx-border-hover)' : 'var(--gx-idle-bar)',
                  borderRadius: '2px 2px 0 0',
                }}
              />
              {hover === k && (
                <div className="gx-bar-tip" style={tipStyle}>
                  <div style={{ fontWeight: 600 }}>{r.bin}</div>
                  <div className="mono" style={{ fontSize: 11.5, color: 'var(--gx-faint)', marginTop: 2 }}>
                    {(r.share * 100).toFixed(1)}% of damage · {r.cycles.toFixed(0)} cycles
                  </div>
                </div>
              )}
            </div>
          );
        })}
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
