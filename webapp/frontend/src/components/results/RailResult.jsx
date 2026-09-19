import Banner from '../Banner';
import DataTable from '../DataTable';
import Metrics from '../Metrics';
import Panel from '../Panel';
import ReliabilityPanel from '../ReliabilityPanel';
import SaveButton from '../SaveButton';
import Verdict from '../Verdict';
import ChannelChart from '../ChannelChart';
import { COLORS } from '../../theme';
import { downloadCsv } from '../../utils/csv';
import { buildSavedEntry } from '../../utils/savedEntry';

const CLASS_COLOR = { Normal: COLORS.green, 'Side I': COLORS.accent, 'Side II': COLORS.amber };

// The full "here's what we found" body for a Rail Corrugation result — shared by the live
// page and the Saved tab so a saved snapshot gets the exact same chart/table, not a
// stripped summary.
export default function RailResult({ result, isSaved, onSave, onRemove }) {
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
        right={isSaved && <SaveButton entry={entry} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />}
      />

      <Verdict
        headline={result.headline}
        tier={result.tier}
        tierLabel={result.tier_label}
        confidenceLabel={result.confidence_label}
        reasoning={result.reasoning}
      />
      <ReliabilityPanel
        title="How reliable is this?"
        note={result.reliability.note}
        lines={result.reliability.classes}
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
            note: 'vibration strength, Side I vs Side II',
            color: result.csv_prediction !== 'Normal' ? CLASS_COLOR[result.csv_prediction] : undefined },
        ]}
      />

      <Panel
        heading="Axle-box vibration energy, 64 channels"
        sub="Per-channel RMS over the 1 s window. Highlighted channels sit on the predicted rail side."
      >
        <ChannelChart channels={result.channels} predictedSide={result.csv_prediction} />
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
    </>
  );
}

export function downloadRailCsv(result) {
  downloadCsv('rail_predictions.csv', ['file_id', 'prediction'], [[result.file_id, result.csv_prediction]]);
}
