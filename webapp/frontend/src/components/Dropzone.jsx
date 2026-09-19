import { useRef, useState } from 'react';
import Spinner from './Spinner';

// onFile receives a single File normally, or a FileList/array of Files when `multiple` is set.
export default function Dropzone({ label, sub, accept, onFile, disabled = false, multiple = false }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = (files) => {
    if (disabled) return;
    if (!files || !files.length) return;
    onFile(multiple ? Array.from(files) : files[0]);
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
        multiple={multiple}
        disabled={disabled}
        onChange={(e) => { handleFiles(e.target.files); e.target.value = ''; }}
      />
      <div className="gx-dropzone-title">
        {disabled && <Spinner />}
        {disabled ? 'Processing…' : label}
      </div>
      <div className="gx-dropzone-sub">{sub}</div>
    </div>
  );
}
