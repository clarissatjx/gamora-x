import { useState } from 'react';
import { GLOSSARY } from '../glossary';

// A dotted-underline span that reveals a plain-language definition on hover/focus. Falls back
// to plain text if the term isn't in the glossary, so callers don't need to guard for it.
export default function Term({ term, className = '', children }) {
  const [open, setOpen] = useState(false);
  const def = GLOSSARY[term];
  if (!def) return <>{children}</>;

  return (
    <span
      className={`gx-term ${className}`.trim()}
      tabIndex={0}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open && <span className="gx-term-tip" role="tooltip">{def}</span>}
    </span>
  );
}
