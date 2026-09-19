export default function UploadModeToggle({ mode, onChange }) {
  return (
    <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
      <button
        className={`gx-btn${mode === 'single' ? ' gx-btn-accent' : ''}`}
        onClick={() => onChange('single')}
      >
        Single file
      </button>
      <button
        className={`gx-btn${mode === 'batch' ? ' gx-btn-accent' : ''}`}
        onClick={() => onChange('batch')}
      >
        Batch upload
      </button>
    </div>
  );
}
