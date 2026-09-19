import { useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { GLOSSARY } from '../glossary';

// A dotted-underline span that reveals a plain-language definition on hover/focus. Falls back
// to plain text if the term isn't in the glossary, so callers don't need to guard for it.
//
// The tooltip is portaled to <body> and positioned in fixed coordinates, not rendered inline
// as an absolutely-positioned child of the term. Every scrollable panel in this app (the main
// content column, in particular) sets overflowY: auto, which per the CSS spec forces
// overflow-x to auto too — so a tooltip near that column's left/right edge (e.g. "Cycles
// detected", the first metric tile) got silently clipped mid-word. Fixed positioning computed
// from the term's own bounding rect sidesteps that entirely.
export default function Term({ term, className = '', style, children }) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState(null);
  const anchorRef = useRef(null);
  const tipRef = useRef(null);
  const def = GLOSSARY[term];

  useLayoutEffect(() => {
    if (!open) { setPos(null); return; }
    const anchor = anchorRef.current;
    const tip = tipRef.current;
    if (!anchor || !tip) return;
    const a = anchor.getBoundingClientRect();
    const t = tip.getBoundingClientRect();
    const margin = 10;
    const left = Math.max(margin, Math.min(a.left + a.width / 2 - t.width / 2, window.innerWidth - t.width - margin));
    const below = a.bottom + 8;
    const top = below + t.height > window.innerHeight - margin ? a.top - t.height - 8 : below;
    setPos({ top, left });
  }, [open]);

  if (!def) return <>{children}</>;

  return (
    <span
      ref={anchorRef}
      className={`gx-term ${className}`.trim()}
      style={style}
      tabIndex={0}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open && createPortal(
        <span
          ref={tipRef}
          className="gx-term-tip gx-term-tip-fixed"
          role="tooltip"
          style={pos ? { top: pos.top, left: pos.left, visibility: 'visible' } : { top: 0, left: 0, visibility: 'hidden' }}
        >
          {def}
        </span>,
        document.body,
      )}
    </span>
  );
}
