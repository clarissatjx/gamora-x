// A saved result is a full snapshot of what a subsystem page rendered, keyed by
// `${subsystem}:${fileId}` so re-saving the same file updates its entry instead of
// duplicating it. Kept in localStorage only — never sent anywhere.
const KEY = 'gamora:saved-results';

export function loadSaved() {
  try {
    const raw = localStorage.getItem(KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

function persist(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch {
    // Private browsing / storage quota — saves just won't survive a refresh.
  }
}

export function upsertSaved(entry) {
  const next = [entry, ...loadSaved().filter((e) => e.id !== entry.id)];
  persist(next);
  return next;
}

export function removeSaved(id) {
  const next = loadSaved().filter((e) => e.id !== id);
  persist(next);
  return next;
}
