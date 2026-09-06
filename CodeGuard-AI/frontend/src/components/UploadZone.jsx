import { useRef, useState } from "react";
import "./UploadZone.css";

export default function UploadZone({ onUpload, uploading, error }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  function handleFiles(files) {
    const file = files?.[0];
    if (!file) return;
    if (!file.name.endsWith(".zip")) {
      onUpload(null, "Only .zip files are accepted");
      return;
    }
    onUpload(file, null);
  }

  return (
    <div className="upload-wrap">
      <div
        className="upload-zone"
        data-dragging={dragging}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") inputRef.current?.click(); }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".zip"
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
        {uploading ? (
          <>
            <div className="upload-spinner" />
            <p className="upload-title">Scanning project…</p>
            <p className="upload-sub">Extracting archive and running static + security analysis</p>
          </>
        ) : (
          <>
            <div className="upload-icon">⬆</div>
            <p className="upload-title">Drop a project ZIP, or click to browse</p>
            <p className="upload-sub">Static &amp; security analysis runs immediately — no API key required</p>
          </>
        )}
      </div>
      {error && <p className="upload-error">{error}</p>}
    </div>
  );
}
