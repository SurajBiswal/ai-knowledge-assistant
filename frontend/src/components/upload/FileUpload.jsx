import { useRef, useState } from "react";
import documentService from "../../services/documentService";

function FileUpload({ onUploadSuccess }) {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef(null);

  const success = message === "Document uploaded successfully.";

  const doUpload = async (file) => {
    if (!file) return;

    try {
      setUploading(true);
      setMessage("");

      // Same service call/contract as before — only the UI around it changed.
      await documentService.uploadDocument(file);

      setMessage("Document uploaded successfully.");

      if (onUploadSuccess) {
        onUploadSuccess();
      }
    } catch (error) {
      setMessage(
        error.response?.data?.detail ||
          "Failed to upload document."
      );
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    doUpload(file);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragOver(false);
    const file = event.dataTransfer?.files?.[0];
    doUpload(file);
  };

  return (
    <div className="mb-3">
      <input
        ref={inputRef}
        id="document-upload-input"
        type="file"
        onChange={handleFileChange}
        className="hidden"
      />

      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        disabled={uploading}
        className={`w-full flex flex-col items-center justify-center gap-1.5 rounded-md border border-dashed px-3 py-4 text-center transition-colors duration-150
          ${isDragOver
            ? "border-mustard bg-mustard-tint/10"
            : "border-ink-softer hover:border-paper-400"
          }
          ${uploading ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
      >
        <svg className="w-4.5 h-4.5 text-paper-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
        </svg>
        <p className="text-xs text-paper-400 font-mono">
          {uploading ? (
            "Uploading…"
          ) : (
            <>Drop files or <span className="text-mustard underline">browse</span></>
          )}
        </p>
      </button>

      {message && (
        <div className="mt-2">
          <span className={`inline-flex items-center rounded px-2.5 py-1 text-xs font-medium ${success ? "bg-moss-tint text-moss-dark" : "bg-clay-tint text-clay-dark"}`}>
            {message}
          </span>
        </div>
      )}
    </div>
  );
}

export default FileUpload;
