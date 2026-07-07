import { useState } from "react";
import documentService from "../../services/documentService";

function FileUpload({ onUploadSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");

  const success = message === "Document uploaded successfully.";

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
    setMessage("");
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setMessage("Please select a file.");
      return;
    }

    try {
      setUploading(true);
      setMessage("");

      await documentService.uploadDocument(selectedFile);

      setMessage("Document uploaded successfully.");
      setSelectedFile(null);

      // Reset the file input
      document.getElementById("document-upload-input").value = "";

      // Refresh document list
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
    }
  };

  return (
    <div className="border rounded p-4 mb-4">
      <h3 className="text-lg font-semibold mb-3">
        Upload Document
      </h3>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          id="document-upload-input"
          type="file"
          onChange={handleFileChange}
          className="block w-full text-sm text-slate-700 file:mr-4 file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-slate-700 file:rounded-full file:font-medium"
        />
        <button
          onClick={handleUpload}
          disabled={uploading}
          className="inline-flex items-center justify-center rounded-full bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition"
        >
          {uploading ? "Uploading..." : "Upload"}
        </button>
      </div>

      {selectedFile && (
        <p className="mt-3 text-sm text-slate-600 truncate">
          {selectedFile.name}
        </p>
      )}

      {message && (
        <div className="mt-3">
          <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${success ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"}`}>
            {message}
          </span>
        </div>
      )}
    </div>
  );
}

export default FileUpload;