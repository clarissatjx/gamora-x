import { useEffect, useState } from 'react';
import Panel from './Panel';
import { fetchNotes, postNote, deleteNote } from '../utils/notes';

const AUTHOR_KEY = 'gamora:note-author';

function readSavedAuthor() {
  try {
    return localStorage.getItem(AUTHOR_KEY) || '';
  } catch {
    return '';
  }
}

// Shared across the team, not per-browser like Saved/History — one engineer leaves context on
// a run, the next one to open the same file sees it. Keyed by subsystem + file_id, so it's
// attached to "this file's result," not to any one person's session.
export default function NotesPanel({ subsystem, fileId }) {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [author, setAuthor] = useState(readSavedAuthor);
  const [text, setText] = useState('');
  const [posting, setPosting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchNotes(subsystem, fileId)
      .then((data) => { if (!cancelled) setNotes(data); })
      .catch((e) => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [subsystem, fileId]);

  const submit = async (e) => {
    e.preventDefault();
    const cleanAuthor = author.trim();
    const cleanText = text.trim();
    if (!cleanAuthor || !cleanText) return;
    setPosting(true);
    setError(null);
    try {
      const note = await postNote(subsystem, fileId, cleanAuthor, cleanText);
      setNotes((prev) => [...prev, note]);
      setText('');
      try { localStorage.setItem(AUTHOR_KEY, cleanAuthor); } catch { /* ignore */ }
    } catch (e) {
      setError(e.message);
    } finally {
      setPosting(false);
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Remove this note?')) return;
    try {
      await deleteNote(id);
      setNotes((prev) => prev.filter((n) => n.id !== id));
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <Panel heading="Notes" sub="Visible to anyone on the team who opens this file.">
      {loading ? (
        <p className="gx-prose" style={{ color: 'var(--gx-muted)', marginTop: 12 }}>Loading notes…</p>
      ) : notes.length === 0 ? (
        <p className="gx-prose" style={{ color: 'var(--gx-muted)', marginTop: 12 }}>
          No notes yet — leave one for the next engineer who looks at this file.
        </p>
      ) : (
        <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {notes.map((n) => (
            <div key={n.id} className="gx-note-row">
              <div className="gx-note-head">
                <span style={{ fontWeight: 600, fontSize: 13.5 }}>{n.author}</span>
                <span className="mono" style={{ fontSize: 11.5, color: 'var(--gx-faint)' }}>
                  {new Date(n.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                </span>
              </div>
              <p className="gx-prose" style={{ marginTop: 5 }}>{n.text}</p>
              <button className="gx-note-remove" onClick={() => remove(n.id)}>Remove</button>
            </div>
          ))}
        </div>
      )}

      {error && <div className="gx-alert" style={{ marginTop: 12 }}><span className="gx-alert-icon">✕</span>{error}</div>}

      <form
        onSubmit={submit}
        style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--gx-border)', display: 'flex', flexDirection: 'column', gap: 8 }}
      >
        <input
          className="gx-input"
          placeholder="Your name"
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          maxLength={60}
        />
        <textarea
          className="gx-input"
          placeholder="Add a note for the team…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          maxLength={2000}
        />
        <button
          className="gx-btn gx-btn-accent"
          type="submit"
          disabled={posting || !author.trim() || !text.trim()}
          style={{ alignSelf: 'flex-start' }}
        >
          {posting ? 'Adding…' : 'Add note'}
        </button>
      </form>
    </Panel>
  );
}
