import { useState } from 'react';

// Same dotted-underline hover as Term, but for a one-off label + tip rather than a glossary
// lookup — used for the "How reliable is this?" note inline in the verdict.
export default function HoverNote({ label, tip, className = '' }) {
  const [open, setOpen] = useState(false);
  return (
    <span
      className={`gx-term ${className}`.trim()}
      tabIndex={0}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {label}
      {open && <span className="gx-term-tip" role="tooltip">{tip}</span>}
    </span>
  );
}
