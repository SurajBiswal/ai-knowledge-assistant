import api from "./api";

const documentService = {
  // Service methods for handling document operations
  async uploadDocument(file) {
    // Implementation for uploading a document
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post(
      "/api/documents/upload",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
    return response.data;
  },

  async getDocuments() {
    const response = await api.get(
      "/api/documents"
    );

    return response.data;
  },

  async deleteDocument(documentId) {
    const response = await api.delete(
      `/api/documents/${documentId}`
    );

    return response.data;
  },
};

export default documentService;


