import Glossed from './Glossed';

export default function Banner({ text, icon = '✓', color = 'var(--gx-accent)', right }) {
  return (
    <div className="gx-banner" style={{ borderLeftColor: color }}>
      <span className="gx-banner-i mono" style={{ color }}>{icon}</span>
      <span className="gx-banner-t"><Glossed text={text} /></span>
      {right && <span style={{ flexShrink: 0 }}>{right}</span>}
    </div>
  );
}
