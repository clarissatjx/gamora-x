import Glossed from './Glossed';
import Panel from './Panel';
import Pill from './Pill';
import { COLORS, tierColor } from '../theme';

// Mirrors app/theme.py::verdict — the plain-language answer read before any chart or metric:
// what happened, how urgent, how sure, why.
export default function Verdict({ headline, tier, tierLabel, confidenceLabel, reasoning }) {
  const color = tierColor(tier);
  return (
    <Panel>
      <div className="gx-verdict-top">
        <div style={{ flex: 1, minWidth: 220 }}>
          <div className="gx-verdict-label">Result</div>
          <div className="gx-verdict-headline" style={{ color }}>{headline}</div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <Pill text={tierLabel} color={color} />
          <Pill text={`Confidence: ${confidenceLabel}`} color={COLORS.faint} />
        </div>
      </div>
      <p className="gx-prose gx-verdict-reasoning"><Glossed text={reasoning} /></p>
    </Panel>
  );
}
