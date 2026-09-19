export default function SaveButton({ entry, isSaved, onSave, onRemove }) {
  const saved = isSaved(entry.id);
  return (
    <button
      className="gx-btn"
      onClick={() => (saved ? onRemove(entry.id) : onSave(entry))}
      aria-pressed={saved}
    >
      {saved ? '★ Saved' : '☆ Save'}
    </button>
  );
}
