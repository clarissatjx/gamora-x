// One-line, plain-language definitions for the domain/ML jargon that shows up in verdict text,
// reliability notes and evidence panels. Written for an engineer new to this dataset, not for
// someone who already knows what back-EMF or rainflow counting means.
// Glossed as whole phrases ("rainflow cycles", not "rainflow" + "cycles" separately), so the
// SHM metric label and banner get one tooltip covering the full title.
const RAINFLOW = "Rainflow counting breaks a messy stress signal into discrete load cycles — each "
  + "one peak-to-valley stress swing — so fatigue damage can be counted cycle by cycle instead of "
  + "guessed from the raw signal. These are the rainflow cycles.";

export const GLOSSARY = {
  'abnormal resistance': "The motor is drawing more current (or less back-EMF) than a healthy "
    + "cycle of the same kind of movement would — the electrical signature of something "
    + "physically resisting the door, such as an obstruction, binding track or worn part. It "
    + "does not diagnose which of those it is, only that resistance is higher than expected.",
  'back-EMF': "The voltage a spinning motor generates on its own, opposing the current driving "
    + "it. It falls when the motor is working harder and turning slower under load — a strained "
    + "motor shows lower back-EMF even as current rises.",
  'mid-travel current': "The motor current partway through a door's open or close stroke, away "
    + "from the start/stop transients — the steadiest point to compare a cycle against a healthy "
    + "baseline of the same operation.",
  'cross-validation': "Testing a model on data it wasn't trained on, repeated on different "
    + "splits of the same dataset, to estimate how it'll do on files it has never seen.",
  'out-of-fold': "A prediction made by a version of the model that never saw that particular "
    + "file during training — so a file's own data can't inflate its own score.",
  'held-out': "Data set aside and never used in training or tuning — the only fair way to "
    + "estimate real-world performance.",
  'macro-F1': "The average of each class's own accuracy score (F1), weighted equally regardless "
    + "of how common that class is — so a rare fault class counts as much as the common "
    + "'Normal' class, unlike plain accuracy.",
  confidence: "The model's own estimate of how sure it is, as a probability. High confidence "
    + "means the input looked a lot like cases the model has seen before — it is not a "
    + "guarantee of correctness.",
  'side asymmetry': "The difference in vibration energy between the rail's two sides (Side I "
    + "minus Side II). Near zero is healthy; a large value points to corrugation on whichever "
    + "side is higher.",
  'cooling setpoint': "The cabin temperature the air-conditioning unit is trying to reach. A car "
    + "stuck well above its setpoint while its neighbours reach theirs is the signature of lost "
    + "refrigerant.",
  'rainflow cycles': RAINFLOW,
  'rainflow counting': RAINFLOW,
  'S-N exponent': "How steeply a material's fatigue life drops as stress swings get bigger, "
    + "from its stress-life (S-N) curve. A higher exponent means large swings do "
    + "disproportionately more damage than small ones.",
  'regressor correction': "A small learned adjustment applied on top of the physics-based "
    + "damage estimate, fitted to close the gap between the formula's raw output and the true "
    + "labelled damage.",
  'fatigue life': "How much cyclic stress a component can endure before failing. A cumulative "
    + "damage value of 1.0 means that budget is fully used up.",
  'IoU-F1': "Intersection-over-Union F1: credit for a predicted time segment is the fraction it "
    + "overlaps the true one, so exact timing matters, not just picking the right cycle.",
  rank: "Partial credit for ranking the true faulty car near the top even if not picked first — "
    + "full credit for 1st place, less for each rank further down.",
  '1−MAPE': "One minus the average percentage error of the damage predictions — 0% error "
    + "scores 1.0, a 10% average error scores 0.90.",
};

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

const TERM_KEYS = Object.keys(GLOSSARY).sort((a, b) => b.length - a.length);
const TERM_RE = new RegExp(`(${TERM_KEYS.map(escapeRegExp).join('|')})`, 'gi');

// Splits `text` into segments, marking only the FIRST occurrence of each recognised term so a
// paragraph that repeats a word (e.g. "confidence" three times) doesn't get glossed three times.
export function glossify(text) {
  const used = new Set();
  const segments = [];
  let cursor = 0;
  const re = new RegExp(TERM_RE);
  let m;
  while ((m = re.exec(text)) !== null) {
    const key = TERM_KEYS.find((k) => k.toLowerCase() === m[0].toLowerCase());
    if (m.index > cursor) segments.push({ text: text.slice(cursor, m.index) });
    if (key && !used.has(key)) {
      used.add(key);
      segments.push({ text: m[0], term: key });
    } else {
      segments.push({ text: m[0] });
    }
    cursor = m.index + m[0].length;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor) });
  return segments;
}
