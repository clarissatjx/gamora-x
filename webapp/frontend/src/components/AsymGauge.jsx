// Where this recording's side imbalance sits, against the three populations measured on the
// labelled data (PLAN.md Phase 10). Drawn as overlapping bands on one axis because the
// overlap IS the message: 94% of the healthy band is also Side I territory, while Side II
// does not overlap healthy at all — which is why one call is trustworthy and the other is a
// judgement. That reads in a second; it takes three paragraphs to say in words.
//
// Deliberately not a per-channel chart: per-car asymmetry is dominated by car-to-car
// variation (PLAN.md Phase 10), so a hotspot view would invite hunting for a bad wheel that
// does not exist in this data.
//
// Colour marks WHICH population a band is, never how worried to be. Healthy is neutral, not
// green: green is the "no action needed" tier colour elsewhere in this app, and a green zone
// here would read as a clean bill of health — which this axis cannot give.
const BAND_COLOR = {
  'Side I corrugation': 'var(--gx-accent)',
  'Side II corrugation': 'var(--gx-amber)',
  'healthy track': 'var(--gx-muted)',
};

// Fixed reference populations, not per-recording values — measured once on the 233 labelled
// moving recordings (PLAN.md Phase 10, mirrored in app/reliability.py::RAIL_ASYM_BANDS). The
// backend sends them so there is one source of truth; duplicated here so a result saved
// before the API carried them still renders.
const FALLBACK_BANDS = [
  { label: 'Side II corrugation', lo: -0.173, hi: -0.045, mean: -0.109, n: 24 },
  { label: 'healthy track', lo: -0.038, hi: 0.029, mean: -0.005, n: 196 },
  { label: 'Side I corrugation', lo: -0.034, hi: 0.096, mean: 0.031, n: 14 },
];
const FALLBACK_AXIS = [-0.20, 0.17];

// `value` is optional: with one, this marks where a specific recording sits; without one it
// is a pure explainer of why the two fault classes are not equally detectable, which is how
// the "Under the hood" page uses it.
export default function AsymGauge({ value, bands, axis, corroborates, prediction, verdictColor }) {
  const hasValue = Number.isFinite(value);
  const useBands = bands?.length ? bands : FALLBACK_BANDS;
  const [lo, hi] = axis?.length === 2 ? axis : FALLBACK_AXIS;
  const pct = (v) => Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100));
  const here = hasValue ? pct(value) : null;

  // Where healthy and Side I overlap, this axis genuinely cannot separate them — and that is
  // 94% of the healthy band. Drawing it stops "my needle is in healthy" reading as "I'm fine".
  const healthy = useBands.find((b) => b.label === 'healthy track');
  const sideI = useBands.find((b) => b.label === 'Side I corrugation');
  const blur = healthy && sideI
    ? { lo: Math.max(healthy.lo, sideI.lo), hi: Math.min(healthy.hi, sideI.hi) }
    : null;
  const inBlur = hasValue && blur && value >= blur.lo && value <= blur.hi;

  // A centred label overflows the panel at the extremes — pin it to whichever edge stays on
  // screen, the same way the old channel tooltip did.
  const anchorStyle = !hasValue ? undefined
    : here < 18 ? { transform: 'none' }
    : here > 82 ? { transform: 'translateX(-100%)' }
    : undefined;
  const trackLeft = (p) =>
    `calc(var(--gx-gauge-gutter) + (100% - var(--gx-gauge-gutter)) * ${p / 100})`;

  return (
    <div className="gx-gauge">
      {/* The marker label gets its own strip rather than floating over the bands, so it
          cannot land on the panel text above or the axis below. */}
      {hasValue && (
      <div className="gx-gauge-head">
        <div className="gx-gauge-marker" style={{ left: trackLeft(here) }}>
          <span
            className="gx-gauge-marker-text"
            style={{ ...anchorStyle, color: verdictColor || 'var(--gx-text)' }}
          >
            This recording
          </span>
          <span
            className="gx-gauge-marker-caret"
            style={{ borderTopColor: verdictColor || 'var(--gx-text)' }}
          />
        </div>
      </div>
      )}

      <div className="gx-gauge-rows">
        {blur && (
          <div
            className="gx-gauge-blur"
            style={{
              left: trackLeft(pct(blur.lo)),
              width: `calc((100% - var(--gx-gauge-gutter)) * ${(pct(blur.hi) - pct(blur.lo)) / 100})`,
            }}
          />
        )}
        {useBands.map((b) => {
          const color = BAND_COLOR[b.label] ?? 'var(--gx-idle-bar)';
          const inside = hasValue && value >= b.lo && value <= b.hi;
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
                    background: `color-mix(in srgb, ${color} ${inside ? 30 : 14}%, transparent)`,
                    borderColor: `color-mix(in srgb, ${color} ${inside ? 70 : 32}%, transparent)`,
                  }}
                />
              </div>
            </div>
          );
        })}
        {hasValue && (
          <div className="gx-gauge-needle" style={{ left: trackLeft(here) }}>
            <div
              className="gx-gauge-needle-line"
              style={{ background: verdictColor || 'var(--gx-text)' }}
            />
          </div>
        )}
      </div>

      <div className="gx-gauge-axis">
        <span className="gx-gauge-axis-end" style={{ left: 0 }}>Side II louder</span>
        {/* A single worded reference: the numeric ticks collided with the end labels and
            nothing depends on reading them now that both ends are named. */}
        <span className="gx-gauge-tick" style={{ left: `${pct(0)}%` }}>sides equal</span>
        <span className="gx-gauge-axis-end" style={{ right: 0 }}>Side I louder</span>
      </div>

      {blur && (
        <div className="gx-gauge-legend">
          <span className="gx-gauge-swatch" />
          <span>
            In this stretch, healthy and Side I recordings look the same on this measure. It
            covers most of the healthy range, so landing there does not clear a recording.
          </span>
        </div>
      )}

      <p className="gx-gauge-caption">
        Each band covers roughly the middle two-thirds of that group of labelled recordings.
        Side II sits clear of healthy; Side I sits on top of it.
        {hasValue && inBlur && ' This recording falls in the overlap, so the verdict above rests on the other signals the model weighs, not on this one.'}
        {hasValue && corroborates === false && !inBlur && prediction && prediction !== 'Normal'
          && ` Its imbalance does not single out ${prediction} on its own — the model reached that verdict from the wider vibration pattern.`}
        {!hasValue && ' That is why Side II is detected well and Side I is not: 63% of all recordings land in the overlap, where this measure cannot separate them.'}
      </p>
    </div>
  );
}
