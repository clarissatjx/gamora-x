// Plain div bars rather than a charting library for this prototype — 64 fixed-order
// channels don't need axes/zoom/tooltips-on-hover beyond a title attribute.
export default function ChannelChart({ channels, predictedSide }) {
  const max = Math.max(...channels.map((c) => c.rms));
  return (
    <div className="gx-chart">
      {channels.map((c) => {
        const hot = c.side === predictedSide;
        const color = hot
          ? (predictedSide === 'Side I' ? 'var(--gx-accent)' : 'var(--gx-amber)')
          : 'var(--gx-idle-bar)';
        return (
          <div
            key={c.channel}
            className="gx-chart-bar"
            title={`${c.channel} · ${c.side} · RMS ${c.rms.toFixed(3)}`}
            style={{ height: `${(c.rms / max) * 100}%`, background: color }}
          />
        );
      })}
    </div>
  );
}
