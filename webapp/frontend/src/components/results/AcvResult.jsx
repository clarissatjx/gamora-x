import Banner from '../Banner';
import GapChart from '../GapChart';
import Metrics from '../Metrics';
import NotesPanel from '../NotesPanel';
import Panel from '../Panel';
import RankingBars from '../RankingBars';
import SaveButton from '../SaveButton';
import UploadNewButton from '../UploadNewButton';
import Verdict from '../Verdict';
import { COLORS } from '../../theme';
import { RELIABILITY_NOTE } from '../../reliabilityNotes';
import { buildSavedEntry } from '../../utils/savedEntry';
import { downloadCsv } from '../../utils/csv';

// The full "here's what we found" body for an ACV result — shared by the live page and the
// Saved tab so a saved snapshot gets the exact same ranking/chart, not a stripped summary.
export default function AcvResult({ result, isSaved, onSave, onRemove, onUploadNew, uploading }) {
  const entry = buildSavedEntry('acv', result);
  return (
    <>
      <Banner
        text={`${result.file_id} accepted — ${result.n_cars} cars over ${result.hours.toFixed(1)} h. `
          + `Ranking complete: car ${result.top} most likely faulty.`}
        right={<>
          {onUploadNew && <UploadNewButton accept=".xlsx" onFile={onUploadNew} loading={uploading} />}
          {isSaved && <SaveButton entry={entry} isSaved={isSaved} onSave={onSave} onRemove={onRemove} />}
        </>}
      />

      <Verdict
        headline={result.headline}
        tier={result.tier}
        tierLabel={result.tier_label}
        confidenceLabel={result.confidence_label}
        reasoning={result.reasoning}
        reliabilityNote={RELIABILITY_NOTE.acv}
      />

      <Metrics
        items={[
          { label: 'Most likely faulty', value: `Car ${result.top}`, note: `score ${result.scores[0].score >= 0 ? '+' : ''}${result.scores[0].score.toFixed(2)}`, color: COLORS.red },
          { label: 'Cars evaluated', value: String(result.n_cars), note: 'IDs read from column headers' },
          { label: 'Gap to runner-up', value: result.margin.toFixed(2), note: `car ${result.runner_up} scores ${result.scores[1].score >= 0 ? '+' : ''}${result.scores[1].score.toFixed(2)}` },
          { label: 'Cabin above setpoint', value: result.gap_top === null ? '—' : `${result.gap_top >= 0 ? '+' : ''}${result.gap_top.toFixed(2)} °C`, note: `car ${result.top}, cooling mode`, color: result.gap_top > 0 ? COLORS.red : undefined },
        ]}
      />

      <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 380px' }}>
          <Panel heading="Ranked cars — most to least likely leak">
            <RankingBars scores={result.scores} />
          </Panel>
        </div>
        <div style={{ flex: '1.15 1 420px' }}>
          {result.chart ? (
            <Panel heading="Cabin temperature vs setpoint, cooling mode"
                   sub="Dashed line is the setpoint. Red is the top-ranked car; the grey band spans the other cars.">
              <GapChart points={result.chart.points} topCar={result.top} hours={result.hours} />
            </Panel>
          ) : (
            <Panel heading="Cabin temperature vs setpoint">
              <p className="gx-prose" style={{ color: 'var(--gx-muted)' }}>
                This workbook carries no cabin-temperature channel, so the ranking comes from
                the peer-deviation heuristic alone.
              </p>
            </Panel>
          )}
        </div>
      </div>

      <NotesPanel subsystem="acv" fileId={result.file_id} />
    </>
  );
}

export function downloadAcvCsv(result) {
  downloadCsv('acv_predictions.csv', ['file_id', 'ranked_cars'], [[result.file_id, result.ranked_cars.join('|')]]);
}
