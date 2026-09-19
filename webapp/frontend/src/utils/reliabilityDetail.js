async function callApi(path) {
  const res = await fetch(path);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

// The full, sourced reliability text — fetched live from app/reliability.py via the backend
// rather than copied into JS, so the "Under the hood" page can't drift out of sync with the
// single source of truth the rest of the codebase already enforces.
export function fetchReliabilityDetail() {
  return callApi('/api/reliability');
}
