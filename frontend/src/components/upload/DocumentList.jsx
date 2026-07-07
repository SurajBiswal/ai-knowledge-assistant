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
    return <p>Loading documents...</p>;
  }

  return (
    <div className="border rounded-2xl p-4 mt-4 bg-slate-50">
      <h3 className="text-lg font-semibold mb-4">
        Documents
      </h3>

      {error && (
        <p className="text-red-600 mb-3">
          {error}
        </p>
      )}

      {documents.length === 0 ? (
        <p>No documents uploaded yet.</p>
      ) : (
        <ul className="space-y-3">
          {documents.map((document) => (
            <li
              key={document.id}
              className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 text-slate-900 text-sm font-semibold truncate">
                    <span>📄</span>
                    <span className="truncate">{document.filename}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {document.file_type.toUpperCase()} • {(document.file_size / 1024).toFixed(1)} KB • Uploaded
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(document.id)}
                  className="mt-1 inline-flex h-9 w-9 items-center justify-center rounded-full bg-rose-50 text-rose-600 transition hover:bg-rose-100 hover:text-rose-800"
                  aria-label={`Delete ${document.filename}`}
                >
                  🗑
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