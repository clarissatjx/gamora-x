import { useCallback, useState } from 'react';
import { loadHistory, recordRun, clearHistory, renameRun } from '../utils/runHistory';

// Local to each subsystem page (unlike useSavedResults) — a page's history key is never
// written by any other page, so there's no cross-tab staleness to guard against here.
export default function useRunHistory(subsystem) {
  const [history, setHistory] = useState(() => loadHistory(subsystem));

  const record = useCallback((result) => setHistory(recordRun(subsystem, result)), [subsystem]);
  const clear = useCallback(() => setHistory(clearHistory(subsystem)), [subsystem]);
  const rename = useCallback((id, label) => setHistory(renameRun(subsystem, id, label)), [subsystem]);

  return { history, record, clear, rename };
}
