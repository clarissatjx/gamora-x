import { useRef } from 'react';
import Spinner from './Spinner';

// Sits next to Save at the top of a result — lets an engineer swap in a different file without
// scrolling down to Reset first. Reuses the page's own runFile, so it goes through the exact
// same predict call and error handling as the original upload.
export default function UploadNewButton({ accept, onFile, loading }) {
  const inputRef = useRef(null);

  return (
    <>
      <button className="gx-btn" onClick={() => inputRef.current?.click()} disabled={loading}>
        {loading && <Spinner />} {loading ? 'Uploading…' : `Upload new ${accept === '.xlsx' ? 'workbook' : 'CSV'}`}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        disabled={loading}
        style={{ display: 'none' }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.target.value = '';
        }}
      />
    </>
  );
}
