import Banner from '../Banner';
import Caveat from '../Caveat';
import Metrics from '../Metrics';
import NotesPanel from '../NotesPanel';
import Panel from '../Panel';
import SaveButton from '../SaveButton';
import UploadNewButton from '../UploadNewButton';
import Verdict from '../Verdict';
import AsymGauge from '../AsymGauge';
import { COLORS } from '../../theme';
import { RELIABILITY_NOTE } from '../../reliabilityNotes';
import { downloadCsv } from '../../utils/csv';
import { buildSavedEntry } from '../../utils/savedEntry';

const CLASS_COLOR = { Normal: COLORS.green, 'Side I': COLORS.accent, 'Side II': COLORS.amber };

// The full "here's what we found" body for a Rail Corrugation result — shared by the live
// page and the Saved tab so a saved snapshot gets the exact same chart/table, not a
// stripped summary.
// The model's own scores, and what that class's calls have historically been worth. Kept to
// a hover: 88% of moving recordings come back at >=99% confidence, so a permanent chart of
// this would read as a flat 100% nearly every time — and a confident Normal is exactly the
// case where Side I hides, so it would overstate certainty rather than inform.
function probabilityTip(result) {
  const probs = result.probabilities;
  if (!probs) return undefined;
  const ranked = Object.entries(probs).sort((a, b) => b[1] - a[1]);
  const scores = ranked.map(([k, v]) => `${k} ${(v * 100).toFixed(0)}%`).join(', ');
  const record = (result.reliability?.classes ?? [])
    .find((c) => c.label === result.csv_prediction);
  const line = record
    ? ` When this model calls ${record.label}, it is right ${Math.round(record.precision * 100)}% of the time, and it catches ${Math.round(record.recall * 100)}% of the ${record.label} recordings that really are.`
    : '';
  return `The model scored the three answers at ${scores}.${line}`;
}

export default function RailResult({ result, isSaved, onSave, onRemove, onUploadNew, uploading }) {
  const entry = buildSavedEntry('rail', result);
  return (
    <>
      <Banner
        text={`${result.file_id} accepted — 129 columns, 10 kHz, 1.0 s window. ${
          result.stationary
            ? result.explanation
            : `Classified ${result.csv_prediction} with ${(result.confidence_value * 100).toFixed(0)}% confidence.`
        }`}
        color={result.stationary ? COLORS.dim : CLASS_COLOR[result.csv_prediction]}
        icon={result.stationary ? '?' : (result.csv_prediction !== 'Normal' ? '!' : '✓')}
        right={<>
          {onUploadNew && <UploadNewButton accept=".csv" onFile={onUploadNew} loading={uploading} />}
          {isSaved && <SaveButton entry={entry} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />}
        </>}
      />

      <Verdict
        headline={result.headline}
        tier={result.tier}
        tierLabel={result.tier_label}
        confidenceLabel={result.confidence_label}
        reasoning={result.reasoning}
        reliabilityNote={[result.reliability?.class_line, RELIABILITY_NOTE.rail]
          .filter(Boolean).join(' ')}
      />

      {result.speed_context?.caveat && (
        <Caveat title={result.speed_context.caveat.title}>
          {result.speed_context.caveat.body}
        </Caveat>
      )}

      <Metrics
        items={[
          { label: 'Prediction', value: result.prediction,
            note: result.stationary ? 'by rule — train not moving' : 'from the vibration pattern',
            color: result.stationary ? COLORS.dim : CLASS_COLOR[result.csv_prediction] },
          { label: 'Confidence', value: result.stationary ? 'rule' : `${(result.confidence_value * 100).toFixed(0)}%`,
            note: result.stationary ? 'no wheel rotation detected' : 'hover for all three scores',
            tip: result.stationary ? undefined : probabilityTip(result) },
          { label: 'Recording speed', value: `${result.speed_kmh.toFixed(0)} km/h`,
            note: result.speed_context?.note ?? 'from the pulse channel',
            tip: result.speed_context?.tip,
            // An untested speed is the one case where the speed itself qualifies the verdict.
            color: result.speed_context?.band === 'untested' ? COLORS.amber : undefined },
          { label: 'Side asymmetry', value: `${result.asym >= 0 ? '+' : ''}${result.asym.toFixed(3)}`,
            note: result.asym_context
              ? `${result.asym_context.sd_from_healthy.toFixed(1)}x the healthy spread (±${result.asym_context.healthy_sd.toFixed(3)})`
              : 'vibration strength, Side I vs Side II',
            // Only colour this as evidence when it actually agrees with the verdict —
            // asymmetry is an indicator, not the model's main input, and it can disagree.
            color: result.asym_context?.corroborates && result.csv_prediction !== 'Normal'
              ? CLASS_COLOR[result.csv_prediction] : undefined },
        ]}
      />

      <Panel
        heading="Where this recording sits"
        sub="Side imbalance — Side I's vibration energy minus Side II's — against every labelled recording. One of several signals the model weighs, not the verdict itself."
      >
        <AsymGauge
          value={result.asym}
          bands={result.asym_bands}
          axis={result.asym_axis}
          corroborates={result.asym_context?.corroborates}
          prediction={result.csv_prediction}
          verdictColor={result.stationary ? COLORS.dim : CLASS_COLOR[result.csv_prediction]}
        />
      </Panel>


      <NotesPanel subsystem="rail" fileId={result.file_id} />
    </>
  );
}

export function downloadRailCsv(result) {
  downloadCsv('rail_predictions.csv', ['file_id', 'prediction'], [[result.file_id, result.csv_prediction]]);
}
