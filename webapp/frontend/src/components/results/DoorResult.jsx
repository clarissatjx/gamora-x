import Banner from '../Banner';
import DataTable from '../DataTable';
import Metrics from '../Metrics';
import Panel from '../Panel';
import SaveButton from '../SaveButton';
import Verdict from '../Verdict';
import DoorChart from '../DoorChart';
import Glossed from '../Glossed';
import Pill from '../Pill';
import { COLORS } from '../../theme';
import { RELIABILITY_NOTE } from '../../reliabilityNotes';
import { buildSavedEntry } from '../../utils/savedEntry';
import { downloadCsv } from '../../utils/csv';

const ABNORMAL = 'Abnormal resistance';
const STATUS_COLOR = { Normal: COLORS.green, [ABNORMAL]: COLORS.red };

// The full "here's what we found" body for a Door result — shared by the live page and the
// Saved tab so a saved snapshot gets the exact same chart/table, not a stripped summary.
export default function DoorResult({ result, isSaved, onSave, onRemove }) {
  const entry = buildSavedEntry('door', result);
  return (
    <>
      <Banner
        text={`${result.file_id} accepted — ${result.n_rows.toLocaleString()} rows, ${
          Math.floor(result.duration_s / 60)} min ${(result.duration_s % 60).toFixed(1)} s of stream. ${
          result.n_cycles} cycles detected.`}
        right={isSaved && <SaveButton entry={entry} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />}
      />

      <Verdict
        headline={result.headline}
        tier={result.tier}
        tierLabel={result.tier_label}
        confidenceLabel={result.confidence_label}
        reasoning={result.reasoning}
        reliabilityNote={RELIABILITY_NOTE.door}
      />

      <Metrics
        items={[
          { label: 'Cycles detected', value: String(result.n_cycles), note: `in ${(result.duration_s / 60).toFixed(1)} min of stream` },
          { label: 'Abnormal resistance', value: String(result.n_abnormal),
            note: `${((result.n_abnormal / Math.max(result.n_cycles, 1)) * 100).toFixed(1)}% of cycles`,
            color: result.n_abnormal ? COLORS.red : undefined },
          { label: 'Mean cycle length', value: `${result.mean_cycle_length.toFixed(2)} s`, note: 'per cycle' },
          { label: 'Mean confidence', value: result.mean_confidence.toFixed(2), note: `lowest ${result.min_confidence.toFixed(2)}` },
        ]}
      />

      <Panel heading="Motor current with detected door cycles"
             sub="Shaded bands are detected cycles, cyan is motor current, the dashed grey line is door leaf position.">
        <DoorChart trace={result.chart.trace} bands={result.chart.bands} />
      </Panel>

      {result.evidence && (
        <Panel heading={result.evidence.title}>
          <div className="gx-ev" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 12 }}>
            {result.evidence.tiles.map((t) => (
              <div key={t.label} style={{ background: 'var(--gx-bg)', border: '1px solid var(--gx-border)', borderRadius: 8, padding: '13px 15px' }}>
                <div style={{ fontSize: 13, color: 'var(--gx-muted)' }}><Glossed text={t.label} /></div>
                <div className="mono" style={{ fontSize: 19, fontWeight: 600, margin: '3px 0', color: COLORS.red }}>{t.value}</div>
                <div className="mono" style={{ fontSize: 12.5, color: 'var(--gx-faint)' }}>{t.note}</div>
              </div>
            ))}
          </div>
          <p className="gx-prose" style={{ marginTop: 12 }}><Glossed text={result.evidence.prose} /></p>
        </Panel>
      )}

      <DataTable
        headers={['#', 'start_time', 'end_time', 'prediction', 'confidence']}
        rows={result.cycles.map((c) => [
          String(c.n).padStart(2, '0'), c.start_time, c.end_time,
          <Pill text={c.prediction} color={STATUS_COLOR[c.prediction]} />,
          c.confidence.toFixed(2),
        ])}
        title={`door_predictions.csv · ${result.cycles.length} rows`}
        schema="start_time, end_time, prediction"
        footer="confidence is informational — only start_time, end_time and prediction are scored."
      />
    </>
  );
}

export function downloadDoorCsv(result) {
  downloadCsv(
    'door_predictions.csv',
    ['start_time', 'end_time', 'prediction', 'confidence'],
    result.cycles.map((c) => [c.start_time, c.end_time, c.prediction, c.confidence]),
  );
}
