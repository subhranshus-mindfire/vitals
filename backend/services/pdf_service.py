"""
PDF & Document Extraction Service for ClinicWorks Platform.

Supports:
1. Digital Searchable PDFs: Fast text extraction via pdftotext / pypdf.
2. Scanned / Image-Based PDFs: Automatically detects image PDFs and converts 
   the page to a Base64-encoded PNG for Azure OpenAI GPT-4o Vision extraction.
3. Plain Text & Image files (.txt, .png, .jpg).
"""

import os
import subprocess
import tempfile
import base64
from pathlib import Path
from typing import Dict, Any, Union


class PDFExtractorService:
    """Extracts content from PDFs and clinical documents, supporting digital text and scanned images."""

    @classmethod
    def process_document(cls, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Universal entry point to process any clinical document (.pdf, .txt, .png, .jpg).
        
        Returns:
            dict: {
                "format": "text" | "image_base64",
                "content": str,   # text string or base64 encoded PNG
                "is_scanned": bool
            }
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return cls.process_pdf(path)
        elif suffix in [".txt", ".csv", ".log"]:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {
                "format": "text",
                "content": content,
                "is_scanned": False
            }
        elif suffix in [".png", ".jpg", ".jpeg"]:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            return {
                "format": "image_base64",
                "content": b64,
                "is_scanned": True
            }
        else:
            # Try reading as text fallback
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return {"format": "text", "content": f.read(), "is_scanned": False}
            except Exception:
                with open(path, "rb") as f:
                    return {"format": "image_base64", "content": base64.b64encode(f.read()).decode("utf-8"), "is_scanned": True}

    @classmethod
    def process_pdf(cls, pdf_source: Union[str, Path, bytes]) -> Dict[str, Any]:
        """
        Processes a PDF file and returns either extracted text or base64 image data.

        Returns:
            dict: {
                "format": "text" | "image_base64",
                "content": str,   # text string or base64 encoded PNG
                "is_scanned": bool
            }
        """
        temp_file = None
        try:
            if isinstance(pdf_source, (str, Path)):
                file_path = str(pdf_source)
            elif isinstance(pdf_source, bytes):
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(pdf_source)
                    temp_file = f.name
                file_path = temp_file
            else:
                raise ValueError(f"Unsupported pdf_source type: {type(pdf_source)}")

            # Step 1: Try digital text extraction first
            text = cls._extract_digital_text(file_path)

            # If digital text exists (> 40 chars), use fast text mode
            if text and len(text.strip()) > 40:
                return {
                    "format": "text",
                    "content": text.strip(),
                    "is_scanned": False
                }

            # Step 2: If text is empty or minimal, treat as Scanned/Image PDF!
            print("📸 Digital text extraction empty or minimal. Falling back to Image-based PDF processing (Vision)...")
            base64_img = cls._convert_pdf_to_base64_image(file_path)
            return {
                "format": "image_base64",
                "content": base64_img,
                "is_scanned": True
            }

        finally:
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)

    @classmethod
    def extract_text(cls, pdf_source: Union[str, Path, bytes]) -> str:
        """Helper to extract text directly from a digital PDF."""
        result = cls.process_pdf(pdf_source)
        if result["format"] == "text":
            return result["content"]
        raise RuntimeError("Document is an image-based scanned PDF with no selectable text. Use process_pdf() or process_document().")

    @staticmethod
    def _extract_digital_text(file_path: str) -> str:
        """Extracts text using pdftotext or pypdf fallback."""
        try:
            result = subprocess.run(
                ["pdftotext", "-layout", file_path, "-"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return result.stdout
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            pass

        return ""

    @staticmethod
    def _convert_pdf_to_base64_image(file_path: str) -> str:
        """Converts the first page of a PDF into a Base64-encoded PNG image using pdftoppm."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_prefix = os.path.join(tmpdir, "page")
            subprocess.run(
                ["pdftoppm", "-png", "-r", "150", "-f", "1", "-l", "1", file_path, output_prefix],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            png_files = sorted(Path(tmpdir).glob("page-*.png"))
            if not png_files:
                raise RuntimeError("Failed to convert scanned PDF to image using pdftoppm.")

            with open(png_files[0], "rb") as img_f:
                image_bytes = img_f.read()

            return base64.b64encode(image_bytes).decode("utf-8")
