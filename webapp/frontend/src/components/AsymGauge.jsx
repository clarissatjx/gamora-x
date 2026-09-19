// Where this recording's side imbalance sits, against the three populations measured on the
// labelled data (PLAN.md Phase 10). Drawn as overlapping bands on one axis because the
// overlap IS the message: Side I's band lies almost entirely on top of healthy, Side II's
// barely touches it — which is why a Side II call is trustworthy and a Side I call is a
// judgement. That reads in a second; it takes three paragraphs to say in words.
//
// Deliberately not a per-channel chart: per-car asymmetry is dominated by car-to-car
// variation (PLAN.md Phase 10), so a hotspot view would invite hunting for a bad wheel
// that does not exist in this data.
const BAND_COLOR = {
  'Side I corrugation': 'var(--gx-accent)',
  'Side II corrugation': 'var(--gx-amber)',
  'healthy track': 'var(--gx-green)',
};

// These are fixed reference populations, not per-recording values — measured once on the
// 233 labelled moving recordings (subsystems/rail_corrugation/PLAN.md Phase 10, mirrored in
// app/reliability.py::RAIL_ASYM_BANDS). The backend sends them so there is one source of
// truth, but they are duplicated here as a fallback: a result saved before the API carried
// them would otherwise render an empty panel.
const FALLBACK_BANDS = [
  { label: 'Side II corrugation', lo: -0.173, hi: -0.045, mean: -0.109, n: 24 },
  { label: 'healthy track', lo: -0.038, hi: 0.029, mean: -0.005, n: 196 },
  { label: 'Side I corrugation', lo: -0.034, hi: 0.096, mean: 0.031, n: 14 },
];
const FALLBACK_AXIS = [-0.20, 0.17];

export default function AsymGauge({ value, bands, axis, corroborates, prediction }) {
  if (!Number.isFinite(value)) return null;
  const useBands = bands?.length ? bands : FALLBACK_BANDS;
  const [lo, hi] = axis?.length === 2 ? axis : FALLBACK_AXIS;
  const pct = (v) => Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100));
  const here = pct(value);
  const ticks = [-0.15, -0.10, -0.05, 0, 0.05, 0.10, 0.15];

  return (
    <div className="gx-gauge">
      <div className="gx-gauge-rows">
        {useBands.map((b) => {
          const color = BAND_COLOR[b.label] ?? 'var(--gx-idle-bar)';
          const inside = value >= b.lo && value <= b.hi;
          return (
            <div className="gx-gauge-row" key={b.label}>
              <div className="gx-gauge-name" style={{ color: inside ? 'var(--gx-text)' : undefined }}>
                {b.label}
                <span className="gx-gauge-n">n={b.n}</span>
              </div>
              <div className="gx-gauge-track">
                <div
                  className="gx-gauge-band"
                  style={{
                    left: `${pct(b.lo)}%`,
                    width: `${pct(b.hi) - pct(b.lo)}%`,
                    background: `color-mix(in srgb, ${color} ${inside ? 28 : 14}%, transparent)`,
                    borderColor: `color-mix(in srgb, ${color} ${inside ? 65 : 32}%, transparent)`,
                  }}
                />
                <div className="gx-gauge-bandmean" style={{ left: `${pct(b.mean)}%`, background: color }} />
              </div>
            </div>
          );
        })}
        {/* One line through all three rows — you read which bands it passes through. */}
        <div className="gx-gauge-needle" style={{ left: `calc(var(--gx-gauge-gutter) + (100% - var(--gx-gauge-gutter)) * ${here / 100})` }}>
          <div className="gx-gauge-needle-line" />
          <div className="gx-gauge-needle-tag mono">
            {value >= 0 ? '+' : ''}{value.toFixed(3)}
          </div>
        </div>
      </div>

      <div className="gx-gauge-axis">
        {ticks.map((t) => (
          <span key={t} className="gx-gauge-tick" style={{ left: `${pct(t)}%` }}>
            {t === 0 ? '0' : t.toFixed(2)}
          </span>
        ))}
      </div>

      <p className="gx-gauge-caption">
        Each band is where that group of labelled recordings sat, give or take its normal
        spread. Side I overlaps healthy almost entirely — that is why light Side I corrugation
        is the hardest call this model makes.
        {corroborates === false && prediction && prediction !== 'Normal' && (
          <> This recording&rsquo;s imbalance does <strong>not</strong> single out {prediction};
          the model reached that verdict from the wider vibration pattern instead, so this gauge
          will not look like the answer.</>
        )}
      </p>
    </div>
  );
}
