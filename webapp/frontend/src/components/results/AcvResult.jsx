import { useEffect, useState } from 'react';
import Banner from '../Banner';
import GapChart from '../GapChart';
import Glossed from '../Glossed';
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

const SCORE_EXPLAINER_PARAGRAPHS = [
  "Each car's score is worked out by comparing it only against its 7 neighbours on the same "
    + "train — never against a fixed pass/fail threshold. Two clues are combined:",
  "Clue 1 — the physics gap. For every car, take (cabin temperature − cooling setpoint) "
    + "averaged over the timestamps it's actively in a cooling mode. This is the direct sign "
    + "of a leak: a unit that's lost refrigerant can't pull its cabin down to target, so this "
    + "gap runs positive and large for the faulty car.",
  "Clue 2 — the heuristic. Around 25 individual measurements are computed per car, grouped "
    + "into a few categories: temperature deviation, refrigerant pressure deviation (where the "
    + "file has it), control-mode behaviour (how often it disagrees with or switches modes "
    + "relative to peers), and fault/invalid-reading flags. Each measurement is converted into "
    + "'how far this car sits from the group's average, in the group's own spread' (a z-score "
    + "against the other 7 cars in that file), and only counted when the car is worse than "
    + "average — being unusually quiet on one measurement shouldn't cancel out being loud on "
    + "another. These ~25 z-scored measurements are then combined into one number as a "
    + "weighted average, with weights chosen by how strong a leak symptom each measurement is: "
    + "temperature, pressure, and fault-related measurements carry the most weight (around "
    + "1.0–1.5), control-mode measurements carry medium weight (around 0.8–1.2), and smaller/"
    + "indirect signals like door-closed disagreement carry the least (around 0.5).",
  "Both clues are z-scored within the file and averaged together 50/50 into one final score "
    + "per car. A higher score just means 'stands out more from its neighbours on this train' "
    + "— so it's normal for more than one car to score positive even though only one is ever "
    + "actually faulty; what matters is which car scores highest, since that ordering is what "
    + "gets submitted as the ranking.",
];

// The full "here's what we found" body for an ACV result — shared by the live page and the
// Saved tab so a saved snapshot gets the exact same ranking/chart, not a stripped summary.
export default function AcvResult({ result, isSaved, onSave, onRemove, onUploadNew, uploading }) {
  const entry = buildSavedEntry('acv', result);
  const otherIds = result.chart?.other_ids ?? result.ranked_cars.filter((c) => c !== result.top);
  const [compareCar, setCompareCar] = useState('all');
  // A new file lands in the same mounted component (no re-key), so drop back to the default
  // comparison rather than carrying a stale car selection over from the previous upload.
  useEffect(() => { setCompareCar('all'); }, [result.file_id]);
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

      <Panel heading="Ranked cars — most to least likely leak">
        <RankingBars scores={result.scores} />
        {SCORE_EXPLAINER_PARAGRAPHS.map((text, i) => (
          <p key={i} className="gx-prose" style={{
            marginTop: i === 0 ? 14 : 8,
            paddingTop: i === 0 ? 12 : undefined,
            borderTop: i === 0 ? '1px solid var(--gx-border)' : undefined,
            fontSize: 13, color: 'var(--gx-muted)',
          }}>
            <Glossed text={text} />
          </p>
        ))}
      </Panel>

      {result.chart ? (
        <Panel
          heading="Cabin temperature vs setpoint, cooling mode"
          sub={compareCar === 'all'
            ? 'Dashed line is the setpoint. Red is the top-ranked car; the grey band spans the other cars.'
            : `Dashed line is the setpoint. Red is car ${result.top}; blue is car ${compareCar}.`}
          right={
            <select
              className="mono"
              value={compareCar}
              onChange={(e) => setCompareCar(e.target.value)}
              style={{
                background: 'var(--gx-bg)', border: '1px solid var(--gx-border-strong)',
                borderRadius: 3, padding: '5px 8px', fontSize: 12.5, color: 'var(--gx-text)',
              }}
            >
              <option value="all">Compare to: all other cars</option>
              {otherIds.map((id) => (
                <option key={id} value={id}>Compare to: car {id}</option>
              ))}
            </select>
          }
        >
          <GapChart
            points={result.chart.points}
            topCar={result.top}
            hours={result.hours}
            compareCar={compareCar === 'all' ? null : compareCar}
          />
        </Panel>
      ) : (
        <Panel heading="Cabin temperature vs setpoint">
          <p className="gx-prose" style={{ color: 'var(--gx-muted)' }}>
            This workbook carries no cabin-temperature channel, so the ranking comes from
            the peer-deviation heuristic alone.
          </p>
        </Panel>
      )}

      <NotesPanel subsystem="acv" fileId={result.file_id} />
    </>
  );
}

export function downloadAcvCsv(result) {
  downloadCsv('acv_predictions.csv', ['file_id', 'ranked_cars'], [[result.file_id, result.ranked_cars.join('|')]]);
}
