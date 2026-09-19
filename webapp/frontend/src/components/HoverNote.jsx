import { useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

// Same dotted-underline hover as Term, but for a one-off label + tip rather than a glossary
// lookup — the verdict's "How reliable is this?" / "See all three scores", and the metric
// tiles' notes.
//
// Positioned the same way as Term, and for the same reason: every scrollable panel here sets
// overflowY: auto, which per the CSS spec forces overflow-x to auto too, so an inline
// absolutely-positioned tip gets silently clipped near a column edge. Portaling to <body>
// with coordinates computed from the anchor's own rect sidesteps that, and clamping to the
// viewport means neighbouring hovers can't overhang each other either.
//
// `wide` opts into a roomier tip: these carry a sentence or two, where the shared default is
// sized for a short glossary definition.
export default function HoverNote({ label, tip, className = '', wide = false }) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState(null);
  const anchorRef = useRef(null);
  const tipRef = useRef(null);

  useLayoutEffect(() => {
    if (!open) { setPos(null); return; }
    const anchor = anchorRef.current;
    const tipEl = tipRef.current;
    if (!anchor || !tipEl) return;
    const a = anchor.getBoundingClientRect();
    const t = tipEl.getBoundingClientRect();
    const margin = 10;
    const left = Math.max(
      margin,
      Math.min(a.left + a.width / 2 - t.width / 2, window.innerWidth - t.width - margin),
    );
    const below = a.bottom + 8;
    const top = below + t.height > window.innerHeight - margin ? a.top - t.height - 8 : below;
    setPos({ top, left });
  }, [open]);

  return (
    <span
      ref={anchorRef}
      className={`gx-term ${className}`.trim()}
      tabIndex={0}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {label}
      {open && createPortal(
        <span
          ref={tipRef}
          className={`gx-term-tip gx-term-tip-fixed${wide ? ' gx-term-tip--wide' : ''}`}
          role="tooltip"
          style={pos
            ? { top: pos.top, left: pos.left, visibility: 'visible' }
            : { top: 0, left: 0, visibility: 'hidden' }}
        >
          {tip}
        </span>,
        document.body,
      )}
    </span>
  );
}
