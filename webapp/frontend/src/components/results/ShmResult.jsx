import Banner from '../Banner';
import DataTable from '../DataTable';
import Glossed from '../Glossed';
import HistogramChart from '../HistogramChart';
import Metrics from '../Metrics';
import Panel from '../Panel';
import SaveButton from '../SaveButton';
import StressChart from '../StressChart';
import Verdict from '../Verdict';
import { RELIABILITY_NOTE } from '../../reliabilityNotes';
import { buildSavedEntry } from '../../utils/savedEntry';
import { downloadCsv } from '../../utils/csv';

// The full "here's what we found" body for an SHM result — shared by the live page and the
// Saved tab so a saved snapshot gets the exact same chart/table, not a stripped summary.
export default function ShmResult({ result, isSaved, onSave, onRemove }) {
  const entry = buildSavedEntry('shm', result);
  return (
    <>
      <Banner
        text={`${result.file_id} accepted — ${result.n_samples.toLocaleString()} samples, ${
          result.n_reversals.toLocaleString()} reversals, ${result.n_cycles.toFixed(0)} rainflow cycles. Damage estimated.`}
        right={isSaved && <SaveButton entry={entry} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />}
      />
      {result.implausible && (
        <div className="gx-alert gx-alert-amber">
          <span className="gx-alert-icon">⚠</span>
          <span>
            {result.file_id}&rsquo;s stress values (peak {result.peak_abs.toFixed(0)}) fall well
            outside the range of our training files (roughly ±20 to ±55). This may not be an SHM
            stress segment — the damage number below could be meaningless for this file.
          </span>
        </div>
      )}

      <Verdict
        headline={result.headline}
        tier={result.tier}
        tierLabel={result.tier_label}
        confidenceLabel={result.confidence_label}
        reasoning={result.reasoning}
        reliabilityNote={RELIABILITY_NOTE.shm}
      />

      <Metrics
        items={[
          { label: 'Cumulative damage', value: result.damage.toFixed(4), note: '0 = fresh, 1 = life used up', color: 'var(--gx-accent)' },
          { label: 'Rainflow cycles', value: result.n_cycles.toLocaleString(undefined, { maximumFractionDigits: 0 }), note: `${result.n_reversals.toLocaleString()} reversals` },
          { label: 'Peak stress range', value: result.max_range.toFixed(1), note: 'largest single cycle' },
        ]}
      />

      <Panel heading="Dynamic stress time series" sub={`${result.file_id} · ${result.n_samples.toLocaleString()} samples`}>
        <StressChart trace={result.trace} peaks={result.peaks} mean={result.mean} />
        <div style={{ fontSize: 12.5, color: 'var(--gx-faint)', marginTop: 8 }}>
          <Glossed text="Amber rings mark the eight biggest stress swings — because of this material's S-N exponent, a handful of cycles like these carries most of the fatigue damage." />
        </div>
      </Panel>

      <Panel heading="Rainflow cycle histogram" sub="Share of total damage by stress-range bin.">
        <HistogramChart rows={result.histogram} />
      </Panel>

      <DataTable
        headers={['file_id', 'prediction']}
        rows={[[result.file_id, result.damage.toFixed(6)]]}
        title="shm_predictions.csv · 1 row"
        schema="file_id, prediction"
        footer="prediction is the cumulative fatigue damage; 1.0 = fatigue life consumed."
      />
    </>
  );
}

export function downloadShmCsv(result) {
  downloadCsv('shm_predictions.csv', ['file_id', 'prediction'], [[result.file_id, result.damage.toFixed(6)]]);
}
