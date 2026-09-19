import HoverNote from './HoverNote';

// The model's own output, rather than a proxy for it. An earlier version of this panel
// plotted side asymmetry against the labelled populations, but 63% of recordings land where
// that measure cannot separate healthy from Side I (PLAN.md Phase 10) — so two uploads in
// three got a chart that said nothing. Probabilities always say something, cannot contradict
// the verdict above, and read without any prior knowledge.
//
// The bar says what the model thinks; the hover says what that is historically worth, which
// differs sharply by class (Side I recall 0.50 against Side II's 0.83).
const CLASS_COLOR = {
  'Side I': 'var(--gx-accent)',
  'Side II': 'var(--gx-amber)',
  Normal: 'var(--gx-muted)',
};

function trackRecord(cls, stats) {
  if (!stats) return null;
  return `Across the labelled recordings, this model caught ${Math.round(stats.recall * 100)}% `
    + `of the recordings that really were ${cls}, and when it does call ${cls} it is right `
    + `${Math.round(stats.precision * 100)}% of the time.`;
}

export default function ClassProbabilities({ probabilities, reliability, predicted }) {
  if (!probabilities) return null;

  const stats = Object.fromEntries((reliability?.classes ?? []).map((c) => [c.label, c]));
  const rows = Object.entries(probabilities)
    .map(([label, p]) => ({ label, p }))
    .sort((a, b) => b.p - a.p);

  const [top, second] = rows;
  const margin = top && second ? top.p - second.p : null;

  return (
    <div className="gx-prob">
      {rows.map(({ label, p }) => {
        const record = trackRecord(label, stats[label]);
        const isTop = label === predicted;
        return (
          <div className="gx-prob-row" key={label}>
            <div className="gx-prob-name" style={{ color: isTop ? 'var(--gx-text)' : undefined }}>
              {record
                ? <HoverNote label={label} tip={record} />
                : label}
            </div>
            <div className="gx-prob-track">
              <div
                className="gx-prob-fill"
                style={{
                  width: `${Math.max(p * 100, 0.6)}%`,
                  background: CLASS_COLOR[label] ?? 'var(--gx-muted)',
                  opacity: isTop ? 1 : 0.45,
                }}
              />
            </div>
            <div
              className="gx-prob-val mono"
              style={{ color: isTop ? 'var(--gx-text)' : undefined }}
            >
              {(p * 100).toFixed(0)}%
            </div>
          </div>
        );
      })}

      {margin != null && (
        <p className="gx-prob-foot">
          {margin >= 0.5
            ? `A clear call — ${top.label} leads the next option by ${(margin * 100).toFixed(0)} points.`
            : margin >= 0.2
              ? `${top.label} leads ${second.label} by ${(margin * 100).toFixed(0)} points.`
              : `A close call — only ${(margin * 100).toFixed(0)} points separate ${top.label} from ${second.label}, so treat this one as worth a second look.`}
          {' '}Hover a class name for how often that call has held up.
        </p>
      )}
    </div>
  );
}
