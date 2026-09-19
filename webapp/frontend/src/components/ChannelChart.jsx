import { useState } from 'react';

// Plain div bars rather than a charting library for this prototype — 64 fixed-order
// channels don't need axes/zoom, just a hover readout per channel.
export default function ChannelChart({ channels, predictedSide }) {
  const [hover, setHover] = useState(null);
  const max = Math.max(...channels.map((c) => c.rms));
  const n = channels.length;
  return (
    <div className="gx-chart">
      {channels.map((c, k) => {
        const hot = c.side === predictedSide;
        const color = hot
          ? (predictedSide === 'Side I' ? 'var(--gx-accent)' : 'var(--gx-amber)')
          : 'var(--gx-idle-bar)';
        // Edge bars would push a centered tooltip off the panel — pin it to whichever
        // side stays on screen instead.
        const edge = k < n * 0.15 ? 'left' : k > n * 0.85 ? 'right' : 'center';
        const tipStyle = edge === 'left' ? { left: 0, transform: 'none' }
          : edge === 'right' ? { left: 'auto', right: 0, transform: 'none' }
          : undefined;
        return (
          <div
            key={c.channel}
            className="gx-bar-wrap"
            onMouseEnter={() => setHover(k)}
            onMouseLeave={() => setHover(null)}
          >
            <div
              className="gx-chart-bar"
              style={{ height: `${(c.rms / max) * 100}%`, background: hover === k ? 'var(--gx-accent-hover)' : color }}
            />
            {hover === k && (
              <div className="gx-bar-tip" style={tipStyle}>
                <div style={{ fontWeight: 600 }}>{c.channel}</div>
                <div className="mono" style={{ fontSize: 11.5, color: 'var(--gx-faint)', marginTop: 2 }}>
                  {c.side} · RMS {c.rms.toFixed(3)}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
