import { useEffect, useState } from "react";
import documentService from "../../services/documentService";

function DocumentList({ refreshTrigger = 0 }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError("");

      const data = await documentService.getDocuments();
      setDocuments(data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Failed to load documents."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [refreshTrigger]);

  const handleDelete = async (documentId) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this document?"
    );

    if (!confirmed) {
      return;
    }

    try {
      await documentService.deleteDocument(documentId);

      setDocuments((prevDocuments) =>
        prevDocuments.filter(
          (document) => document.id !== documentId
        )
      );
    } catch (err) {
      alert(
        err.response?.data?.detail ||
        "Failed to delete document."
      );
    }
  };

  if (loading) {
    return <p className="text-xs text-paper-400 font-mono px-1">Loading documents…</p>;
  }

  // File-type-based icon tint — purely cosmetic, falls back to mustard.
  const iconTone = (fileType) => {
    const t = (fileType || "").toLowerCase();
    if (t === "pdf") return "text-clay";
    if (t === "docx" || t === "doc") return "text-moss";
    return "text-mustard";
  };

  return (
    <div className="mt-1">
      {error && (
        <p className="text-clay mb-2 text-xs">
          {error}
        </p>
      )}

      {documents.length === 0 ? (
        <p className="text-xs text-paper-400 px-0.5">No documents uploaded yet.</p>
      ) : (
        <ul className="space-y-0.5">
          {documents.map((document) => (
            <li
              key={document.id}
              className="group rounded-md px-1.5 py-1.5 hover:bg-ink-soft transition-colors duration-150"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex items-start gap-2">
                  <svg className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${iconTone(document.file_type)}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                  </svg>
                  <div className="min-w-0">
                    <div className="text-paper-100 text-sm font-medium truncate">{document.filename}</div>
                    <p className="mt-0.5 text-[11px] text-paper-400 font-mono">
                      {document.file_type.toUpperCase()} · {(document.file_size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(document.id)}
                  className="flex-shrink-0 inline-flex h-6 w-6 items-center justify-center rounded-md text-paper-400 opacity-0 group-hover:opacity-100 transition hover:bg-clay-tint hover:text-clay"
                  aria-label={`Delete ${document.filename}`}
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                  </svg>
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default DocumentList;
