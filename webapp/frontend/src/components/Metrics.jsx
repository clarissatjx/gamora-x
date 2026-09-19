import Glossed from './Glossed';
import HoverNote from './HoverNote';

export default function Metrics({ items }) {
  return (
    <div className="gx-metrics">
      {items.map(({ label, value, note, color, tip }) => (
        <div className="gx-metric" key={label}>
          <div className="gx-metric-l"><Glossed text={label} /></div>
          <div className="gx-metric-v" style={{ color: color || 'var(--gx-text)' }}>
            {/* `tip` carries detail that would crowd the tile — e.g. the full class
                breakdown behind a single confidence figure. */}
            {tip ? <HoverNote label={value} tip={tip} /> : value}
          </div>
          <div className="gx-metric-n">{note && <Glossed text={note} />}</div>
        </div>
      ))}
    </div>
  );
}
