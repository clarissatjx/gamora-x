import Glossed from './Glossed';

// A short "read this before you act on the verdict" note, sitting between the verdict and
// the numbers so it lands in the reading path rather than beside it. Used where a result is
// technically correct but would mislead if taken at face value — e.g. a Normal verdict on a
// recording slower than any fault the model was trained on.
//
// Deliberately not a tooltip: this changes what the engineer should do next, and a hover is
// too easy to walk past.
export default function Caveat({ title, children }) {
  if (!children) return null;
  return (
    <div className="gx-caveat">
      <span className="gx-caveat-mark" aria-hidden="true">!</span>
      <div>
        {title && <div className="gx-caveat-title">{title}</div>}
        <p className="gx-caveat-body">
          {typeof children === 'string' ? <Glossed text={children} /> : children}
        </p>
      </div>
    </div>
  );
}
