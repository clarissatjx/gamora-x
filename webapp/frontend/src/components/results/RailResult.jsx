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
// page and the Saved tab so a saved snapshot gets the same evidence, not a stripped summary.

// What the model made of THIS recording. Deliberately says nothing about the model's track
// record — that is the neighbouring "How reliable is this?" hover, and having both quote the
// same recall and precision figures just says one thing twice.
//
// Kept to a hover rather than a chart: 88% of moving recordings come back at >=99%
// confidence, so a permanent version would read as a flat 100% nearly every time — and a
// confident Normal is exactly the case where Side I hides, so it would overstate certainty
// rather than inform.
function probabilityTip(result) {
  const probs = result.probabilities;
  if (!probs) return undefined;
  const ranked = Object.entries(probs).sort((a, b) => b[1] - a[1]);
  const scores = ranked.map(([k, v]) => `${k} ${(v * 100).toFixed(0)}%`).join(', ');
  const margin = ranked.length > 1 ? (ranked[0][1] - ranked[1][1]) * 100 : null;
  const closeness = margin == null ? ''
    : margin < 20
      ? ` Only ${margin.toFixed(0)} points separate the top two, so this was a close call.`
      : ` The top answer leads the next by ${margin.toFixed(0)} points.`;
  return `For this recording the model scored the three answers at ${scores}.${closeness}`;
}

export default function RailResult({ result, isSaved, onSave, onRemove, onUploadNew, uploading }) {
  const entry = buildSavedEntry('rail', result);
  return (
    <>
      <Banner
        text={`${result.file_id} accepted`}
        detail="129 columns, 10 kHz, a 1.0 second window — the shape this model expects."
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
        reliabilityNote={[RELIABILITY_NOTE.rail, result.reliability?.class_line]
          .filter(Boolean).join(' ')}
        scoresNote={result.stationary ? undefined : probabilityTip(result)}
      />

      {result.speed_context?.caveat && (
        <Caveat title={result.speed_context.caveat.title}>
          {result.speed_context.caveat.body}
        </Caveat>
      )}

      <Metrics
        items={[
          { label: 'Recording speed', value: `${result.speed_kmh.toFixed(0)} km/h`,
            // A stationary recording is already led by "Inconclusive"; telling it that it is
            // slower than any fault we have seen is a strange way to say the train is parked.
            note: result.stationary
              ? 'train not moving'
              : (result.speed_context?.note ?? 'from the pulse channel'),
            tip: result.stationary ? undefined : result.speed_context?.tip,
            // An untested speed is the one case where the speed itself qualifies the verdict.
            color: !result.stationary && result.speed_context?.band === 'untested'
              ? COLORS.amber : undefined },
          { label: 'Side asymmetry', value: `${result.asym >= 0 ? '+' : ''}${result.asym.toFixed(3)}`,
            note: result.asym_context
              ? `${result.asym_context.sd_from_healthy.toFixed(1)}x what healthy track varies by`
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
