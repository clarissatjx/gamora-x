import { useRef, useState } from 'react';
import Spinner from './Spinner';

export default function Dropzone({ label, sub, accept, onFile, disabled = false }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = (files) => {
    if (disabled) return;
    if (files && files.length) onFile(files[0]);
  };

  return (
    <div
      className={`gx-dropzone${dragging ? ' dragging' : ''}${disabled ? ' disabled' : ''}`}
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        disabled={disabled}
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div className="gx-dropzone-title">
        {disabled && <Spinner />}
        {disabled ? 'Processing…' : label}
      </div>
      <div className="gx-dropzone-sub">{sub}</div>
    </div>
  );
}
