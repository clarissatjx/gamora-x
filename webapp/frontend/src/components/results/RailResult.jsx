import Banner from '../Banner';
import DataTable from '../DataTable';
import Metrics from '../Metrics';
import NotesPanel from '../NotesPanel';
import Panel from '../Panel';
import SaveButton from '../SaveButton';
import UploadNewButton from '../UploadNewButton';
import Verdict from '../Verdict';
import SideDistribution from '../SideDistribution';
import { COLORS } from '../../theme';
import { RELIABILITY_NOTE } from '../../reliabilityNotes';
import { downloadCsv } from '../../utils/csv';
import { buildSavedEntry } from '../../utils/savedEntry';

const CLASS_COLOR = { Normal: COLORS.green, 'Side I': COLORS.accent, 'Side II': COLORS.amber };

// The full "here's what we found" body for a Rail Corrugation result — shared by the live
// page and the Saved tab so a saved snapshot gets the exact same chart/table, not a
// stripped summary.
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

      <Metrics
        items={[
          { label: 'Prediction', value: result.prediction,
            note: result.stationary ? 'by rule — train not moving' : 'from the vibration pattern',
            color: result.stationary ? COLORS.dim : CLASS_COLOR[result.csv_prediction] },
          { label: 'Confidence', value: result.stationary ? 'rule' : `${(result.confidence_value * 100).toFixed(0)}%`,
            note: result.stationary ? 'no wheel rotation detected' : 'how sure the model is' },
          { label: 'Recording speed', value: `${result.speed_kmh.toFixed(0)} km/h`, note: 'from the pulse channel' },
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
        heading="How the two rails compare"
        sub="Each dot is one axle box's vibration energy over the 1 s window; the bar marks that side's average. The two spreads overlap heavily — the verdict comes from the shift between their centres, not from any single channel."
      >
        <SideDistribution
          channels={result.channels}
          predictedSide={result.csv_prediction}
          asymContext={result.asym_context}
        />
      </Panel>

      <DataTable
        headers={['file_id', 'prediction', 'confidence', 'speed km/h']}
        rows={[[
          result.file_id,
          <span className="pill" style={{ color: CLASS_COLOR[result.csv_prediction],
            background: `color-mix(in srgb, ${CLASS_COLOR[result.csv_prediction]} 12%, transparent)`,
            border: `1px solid color-mix(in srgb, ${CLASS_COLOR[result.csv_prediction]} 30%, transparent)` }}>
            {result.csv_prediction}
          </span>,
          result.stationary ? 'rule' : result.confidence_value.toFixed(2),
          result.speed_kmh.toFixed(0),
        ]]}
        title="rail_predictions.csv · 1 row"
        schema="file_id, prediction"
        footer="only file_id and prediction are submitted; confidence and speed are informational."
      />

      <NotesPanel subsystem="rail" fileId={result.file_id} />
    </>
  );
}

export function downloadRailCsv(result) {
  downloadCsv('rail_predictions.csv', ['file_id', 'prediction'], [[result.file_id, result.csv_prediction]]);
}
