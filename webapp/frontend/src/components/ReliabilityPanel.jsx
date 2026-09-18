import Panel from './Panel';
import { COLORS } from '../theme';

// Mirrors app/theme.py::reliability_panel — how trustworthy the model has actually been,
// sourced from the subsystem's PLAN.md, shown right under the verdict, not buried away.
export default function ReliabilityPanel({ title, note, lines }) {
  return (
    <Panel heading={title}>
      {lines && lines.map(({ label, recall, precision }) => (
        <div className="gx-rel-row" key={label}>
          <div className="gx-rel-row-head">
            <span>{label}</span>
            <span className="mono" style={{ color: COLORS.faint }}>
              catches {(recall * 100).toFixed(0)}% · right when flagged {(precision * 100).toFixed(0)}%
            </span>
          </div>
          <div className="gx-rel-bar">
            <div className="gx-rel-bar-fill" style={{ flex: Math.max(recall, 0.02) }} />
            <div className="gx-rel-bar-rest" style={{ flex: Math.max(1 - recall, 0.02) }} />
          </div>
        </div>
      ))}
      <p className="gx-prose" style={{ color: COLORS.faint, marginTop: 2 }}>{note}</p>
    </Panel>
  );
}
