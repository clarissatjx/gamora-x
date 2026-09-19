import { useCallback, useState } from 'react';
import { loadSaved, upsertSaved, removeSaved } from '../utils/savedResults';

// Lifted to App so every page shares one list — pages stay mounted when switching tabs
// (see App.jsx), so a per-page instance of this hook would each hold its own stale copy.
export default function useSavedResults() {
  const [saved, setSaved] = useState(loadSaved);

  const save = useCallback((entry) => {
    setSaved(upsertSaved({ ...entry, savedAt: new Date().toISOString() }));
  }, []);
  const remove = useCallback((id) => setSaved(removeSaved(id)), []);
  const isSaved = useCallback((id) => saved.some((e) => e.id === id), [saved]);

  return { saved, save, remove, isSaved };
}
