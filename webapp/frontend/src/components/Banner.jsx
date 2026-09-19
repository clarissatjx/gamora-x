import Glossed from './Glossed';
import HoverNote from './HoverNote';

export default function Banner({ text, detail, icon = '✓', color = 'var(--gx-accent)', right }) {
  return (
    <div className="gx-banner" style={{ borderLeftColor: color }}>
      <span className="gx-banner-i mono" style={{ color }}>{icon}</span>
      <span className="gx-banner-t">
        <Glossed text={text} />
        {/* Format detail is what you need when a file is REJECTED; on a success it is
            trivia sitting above the answer. */}
        {detail && <> · <HoverNote label="file detail" tip={detail} /></>}
      </span>
      {right && <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>{right}</div>}
    </div>
  );
}
