import { useRef, useState } from 'react';

export default function Dropzone({ label, sub, accept, onFile }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = (files) => {
    if (files && files.length) onFile(files[0]);
  };

  return (
    <div
      className={`gx-dropzone${dragging ? ' dragging' : ''}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
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
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div className="gx-dropzone-title">{label}</div>
      <div className="gx-dropzone-sub">{sub}</div>
    </div>
  );
}
