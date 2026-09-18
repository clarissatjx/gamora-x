import Glossed from './Glossed';

export default function Banner({ text, icon = '✓', color = 'var(--gx-accent)' }) {
  return (
    <div className="gx-banner" style={{ borderLeftColor: color }}>
      <span className="gx-banner-i mono" style={{ color }}>{icon}</span>
      <span className="gx-banner-t"><Glossed text={text} /></span>
    </div>
  );
}
