import Glossed from './Glossed';

export default function Banner({ text, icon = '✓', color = 'var(--gx-accent)', right }) {
  return (
    <div className="gx-banner" style={{ borderLeftColor: color }}>
      <span className="gx-banner-i mono" style={{ color }}>{icon}</span>
      <span className="gx-banner-t"><Glossed text={text} /></span>
      {right && <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>{right}</div>}
    </div>
  );
}
