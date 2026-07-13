from pathlib import Path
from pypdf import PdfReader
from docx import Document

class DocumentExtractor:
    def extract(self, file_path: str, file_type: str) -> str:
        """
        Extracts text from a document based on its file type.

        Args:
            file_path (str): The path to the document file.
            file_type (str): The type of the document (e.g., 'pdf', 'docx', 'txt').

        Returns:
            str: The extracted text from the document.
        """

        if not Path(file_path).exists():
            raise FileNotFoundError(f"The file {file_path} does not exist.")
        
        file_type = file_type.lower()

        match file_type:
            case "pdf":
                return self._extract_text_from_pdf(file_path)
            case "docx":
                return self._extract_text_from_docx(file_path)
            case "txt":
                return self._extract_text_from_txt(file_path)
            case _:
                raise ValueError(f"Unsupported file type: {file_type}")



# Extract from PDF---------------------------------------------------------------------------------
    def _extract_text_from_pdf(
    self,
    file_path: str,
    ) -> str:
        """
        Extract text from a PDF document.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Extracted text as a single string.

        Raises:
            RuntimeError: If the PDF cannot be read.
        """

        try:
            reader = PdfReader(file_path)

            pages: list[str] = []

            for page in reader.pages:
                page_text = page.extract_text()

                if page_text:
                    pages.append(page_text)

            text = "\n\n".join(pages)

            if not text.strip():
                raise ValueError(
                    "No extractable text found in the PDF."
                )

            return text

        except Exception as exc:
            raise RuntimeError(
                f"Failed to extract text from PDF: {file_path}"
            ) from exc



# Extract from DOCX---------------------------------------------------------------------------------
    def _extract_text_from_docx(
    self,
    file_path: str,
    ) -> str:
        """
        Extract text from a DOCX document.

        Args:
            file_path: Path to the DOCX file.

        Returns:
            Extracted text as a single string.

        Raises:
            RuntimeError: If the DOCX cannot be read.
        """

        try:
            document = Document(file_path)

            paragraphs: list[str] = []

            for paragraph in document.paragraphs:
                text = paragraph.text.strip()

                if text:
                    paragraphs.append(text)

            extracted_text = "\n\n".join(paragraphs)

            if not extracted_text.strip():
                raise ValueError(
                    "No extractable text found in the DOCX."
                )

            return extracted_text

        except Exception as exc:
            raise RuntimeError(
                f"Failed to extract text from DOCX: {file_path}"
            ) from exc
        


# Extract from TXT---------------------------------------------------------------------------------
    def _extract_text_from_txt(
        self,
        file_path: str,
    ) -> str:
        """
        Extract text from a TXT document.

        Args:
            file_path: Path to the TXT file.

        Returns:
            Extracted text as a single string.

        Raises:
            RuntimeError: If the TXT file cannot be read.
        """

        try:
            text = Path(file_path).read_text(encoding="utf-8")

            if not text.strip():
                raise ValueError(
                    "No extractable text found in the TXT file."
                )

            return text

        except Exception as exc:
            raise RuntimeError(
                f"Failed to extract text from TXT: {file_path}"
            ) from exc