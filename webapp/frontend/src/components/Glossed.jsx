import { glossify } from '../glossary';
import Term from './Term';

// Renders `text` with any recognised jargon terms auto-wrapped in a glossary tooltip. Used
// wherever backend-generated prose (verdict reasoning, reliability notes, banners) is rendered,
// so a new engineer gets an inline definition without the operator's view being cluttered —
// the dotted underline only appears under words the glossary actually knows.
export default function Glossed({ text }) {
  const segments = glossify(text);
  return segments.map((s, i) => (s.term
    ? <Term key={i} term={s.term}>{s.text}</Term>
    : <span key={i}>{s.text}</span>));
}
