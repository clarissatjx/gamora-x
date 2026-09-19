import Glossed from './Glossed';
import HoverNote from './HoverNote';

export default function Metrics({ items }) {
  return (
    <div className="gx-metrics">
      {items.map(({ label, value, note, color, tip }) => (
        <div className="gx-metric" key={label}>
          <div className="gx-metric-l"><Glossed text={label} /></div>
          <div className="gx-metric-v" style={{ color: color || 'var(--gx-text)' }}>{value}</div>
          {/* `tip` carries detail that would crowd the tile — e.g. the full class breakdown
              behind a single confidence figure. It hangs off the note rather than the value:
              the dotted hover underline is invisible under the large display figure. */}
          <div className="gx-metric-n">
            {tip ? <HoverNote label={note} tip={tip} wide /> : note && <Glossed text={note} />}
          </div>
        </div>
      ))}
    </div>
  );
}
