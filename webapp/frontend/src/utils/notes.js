async function callApi(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

// Notes live on the backend (not localStorage) — the whole point is another engineer, on
// another machine, sees them when they open the same file.
export function fetchNotes(subsystem, fileId) {
  return callApi(`/api/notes?subsystem=${encodeURIComponent(subsystem)}&file_id=${encodeURIComponent(fileId)}`);
}

export function postNote(subsystem, fileId, author, text) {
  return callApi('/api/notes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subsystem, file_id: fileId, author, text }),
  });
}

export function deleteNote(id) {
  return callApi(`/api/notes/${id}`, { method: 'DELETE' });
}
