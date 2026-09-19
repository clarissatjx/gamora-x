import Glossed from './Glossed';
import HoverNote from './HoverNote';
import Pill from './Pill';
import { COLORS, tierColor } from '../theme';

// Mirrors app/theme.py::verdict — the plain-language answer read before any chart or metric:
// what happened, how urgent, how sure, why. The flag stripe carries the status at a glance,
// like a signal-lamp aspect, so the reading order doesn't depend on parsing colored text.
export default function Verdict({ headline, tier, tierLabel, confidenceLabel, reasoning, reliabilityNote, scoresNote }) {
  const color = tierColor(tier);
  return (
    <div className="gx-verdict">
      <div className="gx-verdict-flag" style={{ background: color }} />
      <div className="gx-verdict-body">
        <div className="gx-verdict-top">
          <div style={{ flex: 1, minWidth: 220 }}>
            <div className="gx-verdict-label">Result</div>
            <div className="gx-verdict-headline">{headline}</div>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <Pill text={tierLabel} color={color} />
            <Pill text={`Confidence: ${confidenceLabel}`} color={COLORS.faint} />
          </div>
        </div>
        <p className="gx-prose gx-verdict-reasoning"><Glossed text={reasoning} /></p>
        {(reliabilityNote || scoresNote) && (
          <div style={{ fontSize: 12.5, color: 'var(--gx-faint)', marginTop: 10, display: 'flex', gap: 22, rowGap: 6, flexWrap: 'wrap' }}>
            {reliabilityNote && (
              <HoverNote label="How reliable is this?" tip={reliabilityNote} wide />
            )}
            {scoresNote && (
              <HoverNote label="See all three scores" tip={scoresNote} wide />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
