// Auto-logged, per subsystem: every file run through that subsystem (single or batch), most
// recent first. Distinct from saved-results — this is an automatic activity log, not a
// user-curated list, so entries are never deduped by file_id: running the same file twice
// keeps both runs. Capped so localStorage doesn't grow without bound.
const PREFIX = 'gamora:run-history:';
const MAX_ENTRIES = 50;

function key(subsystem) {
  return `${PREFIX}${subsystem}`;
}

export function loadHistory(subsystem) {
  try {
    const raw = localStorage.getItem(key(subsystem));
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

function persist(subsystem, list) {
  try {
    localStorage.setItem(key(subsystem), JSON.stringify(list));
  } catch {
    // Private browsing / storage quota — history just won't survive a refresh.
  }
}

export function recordRun(subsystem, result) {
  const entry = {
    id: `${subsystem}:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`,
    fileId: result.file_id,
    label: result.file_id, // editable display name — starts as the filename, renameable after
    headline: result.headline,
    tier: result.tier,
    tierLabel: result.tier_label,
    ranAt: new Date().toISOString(),
    result,
  };
  const next = [entry, ...loadHistory(subsystem)].slice(0, MAX_ENTRIES);
  persist(subsystem, next);
  return next;
}

export function renameRun(subsystem, id, label) {
  const next = loadHistory(subsystem).map((e) => (e.id === id ? { ...e, label } : e));
  persist(subsystem, next);
  return next;
}

export function deleteRun(subsystem, id) {
  const next = loadHistory(subsystem).filter((e) => e.id !== id);
  persist(subsystem, next);
  return next;
}

export function clearHistory(subsystem) {
  persist(subsystem, []);
  return [];
}
