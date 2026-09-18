export default function Metrics({ items }) {
  return (
    <div className="gx-metrics">
      {items.map(({ label, value, note, color }) => (
        <div className="gx-metric" key={label}>
          <div className="gx-metric-l">{label}</div>
          <div className="gx-metric-v" style={{ color: color || 'var(--gx-text)' }}>{value}</div>
          <div className="gx-metric-n">{note}</div>
        </div>
      ))}
    </div>
  );
}
