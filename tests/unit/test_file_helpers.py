import pytest
import uuid
from unittest.mock import AsyncMock, patch, mock_open
from pathlib import Path
from pydocs.schema.file import (
    get_document_type_from_mime,
    compute_file_checksum,
    save_upload_file,
    validate_file,
    extract_text_metadata,
    extract_pdf_metadata,
)
from pydocs.models import DocumentType
from fastapi import UploadFile, HTTPException
import io


class TestGetDocumentTypeFromMime:
    """Test cases for get_document_type_from_mime function."""

    def test_pdf_document_type(self):
        """Test PDF detection from MIME type."""
        result = get_document_type_from_mime("application/pdf", "document.pdf")
        assert result == DocumentType.PDF

    def test_pdf_document_type_from_extension(self):
        """Test PDF detection from file extension."""
        result = get_document_type_from_mime("application/octet-stream", "document.pdf")
        assert result == DocumentType.PDF

    def test_markdown_document_type(self):
        """Test Markdown detection from MIME type."""
        result = get_document_type_from_mime("text/markdown", "document.md")
        assert result == DocumentType.MARKDOWN

    def test_markdown_document_type_from_extension(self):
        """Test Markdown detection from file extension."""
        result = get_document_type_from_mime("text/plain", "document.md")
        assert result == DocumentType.MARKDOWN

    def test_html_document_type(self):
        """Test HTML detection from MIME type."""
        result = get_document_type_from_mime("text/html", "document.html")
        assert result == DocumentType.HTML

    def test_html_document_type_from_extension(self):
        """Test HTML detection from file extension."""
        result = get_document_type_from_mime("text/plain", "document.htm")
        assert result == DocumentType.HTML

    def test_text_document_type_default(self):
        """Test default text document type."""
        result = get_document_type_from_mime("text/plain", "document.txt")
        assert result == DocumentType.TEXT

    def test_unknown_document_type(self):
        """Test unknown document type falls back to text."""
        result = get_document_type_from_mime("application/unknown", "document.xyz")
        assert result == DocumentType.TEXT


class TestComputeFileChecksum:
    """Test cases for compute_file_checksum function."""

    @pytest.mark.asyncio
    async def test_compute_checksum_small_file(self):
        """Test computing checksum for a small file."""
        test_content = b"Hello, World!"
        expected_checksum = (
            "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        )

        with patch("aiofiles.open", mock_open(read_data=test_content)):
            result = await compute_file_checksum(Path("/fake/path/test.txt"))
            assert result == expected_checksum

    @pytest.mark.asyncio
    async def test_compute_checksum_empty_file(self):
        """Test computing checksum for an empty file."""
        expected_checksum = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"  # SHA256 of empty string

        with patch("aiofiles.open", mock_open(read_data=b"")):
            result = await compute_file_checksum(Path("/fake/path/empty.txt"))
            assert result == expected_checksum


class TestSaveUploadFile:
    """Test cases for save_upload_file function."""

    @pytest.mark.asyncio
    async def test_save_upload_file_success(self):
        """Test successful file saving."""
        # Create a mock UploadFile
        file_content = b"This is test file content"
        upload_file = UploadFile(
            filename="test.txt",
            file=io.BytesIO(file_content),
            content_type="text/plain",
        )

        owner_id = uuid.uuid4()

        with (
            patch("aiofiles.open", mock_open()) as mock_file,
            patch("pydocs.schema.file.settings") as mock_settings,
        ):
            # Mock settings
            mock_settings.UPLOAD_DIR = Path("/tmp/uploads")
            mock_settings.MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

            # Mock file operations
            mock_file_instance = mock_file.return_value.__aenter__.return_value
            mock_file_instance.read.side_effect = [file_content, b""]

            # Call the function
            file_path, file_size, checksum = await save_upload_file(
                upload_file, owner_id
            )

            # Assertions
            assert file_size == len(file_content)
            assert isinstance(file_path, Path)
            assert len(checksum) == 64  # SHA256 hex digest length

    @pytest.mark.asyncio
    async def test_save_upload_file_exceeds_size_limit(self):
        """Test file saving when file exceeds size limit."""
        # Create a mock UploadFile with large content
        large_content = b"x" * (10 * 1024 * 1024 + 1)  # 10MB + 1 byte
        upload_file = UploadFile(
            filename="large.txt",
            file=io.BytesIO(large_content),
            content_type="text/plain",
        )

        owner_id = uuid.uuid4()

        with (
            patch("aiofiles.open", mock_open()) as mock_file,
            patch("pydocs.schema.file.settings") as mock_settings,
            pytest.raises(HTTPException) as exc_info,
        ):
            # Mock settings
            mock_settings.UPLOAD_DIR = Path("/tmp/uploads")
            mock_settings.MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

            # Mock file operations
            mock_file_instance = mock_file.return_value.__aenter__.return_value
            mock_file_instance.read.return_value = large_content

            # Call the function - should raise HTTPException
            await save_upload_file(upload_file, owner_id)

            # Assertions
            assert exc_info.value.status_code == 413


class TestValidateFile:
    """Test cases for validate_file function."""

    def test_validate_valid_file(self):
        """Test validation of a valid file."""
        upload_file = UploadFile(
            filename="document.pdf",
            file=io.BytesIO(b"PDF content"),
            content_type="application/pdf",
        )

        # Should not raise any exception
        validate_file(upload_file)

    def test_validate_file_without_filename(self):
        """Test validation of a file without filename."""
        upload_file = UploadFile(
            filename="",  # Empty filename
            file=io.BytesIO(b"content"),
            content_type="text/plain",
        )

        with pytest.raises(HTTPException) as exc_info:
            validate_file(upload_file)

        assert exc_info.value.status_code == 400

    def test_validate_file_with_invalid_extension(self):
        """Test validation of a file with invalid extension."""
        upload_file = UploadFile(
            filename="malicious.exe",
            file=io.BytesIO(b"executable content"),
            content_type="application/octet-stream",
        )

        with pytest.raises(HTTPException) as exc_info:
            validate_file(upload_file)

        assert exc_info.value.status_code == 400


class TestExtractTextMetadata:
    """Test cases for extract_text_metadata function."""

    @pytest.mark.asyncio
    async def test_extract_text_metadata_utf8(self):
        """Test extracting metadata from UTF-8 text file."""
        test_content = "Hello\nWorld\nThis is a test file.\nWith multiple lines."

        with patch("aiofiles.open", mock_open(read_data=test_content)):
            result = await extract_text_metadata(Path("/fake/path/test.txt"))

            assert result["line_count"] == 4
            assert result["word_count"] == 12
            assert result["encoding"] == "utf-8"
            assert "content_preview" in result

    @pytest.mark.asyncio
    async def test_extract_text_metadata_latin1_fallback(self):
        """Test extracting metadata with Latin-1 fallback."""
        # Content that would cause UnicodeDecodeError with UTF-8
        test_content = "Café\nRésumé\nNaïve"  # Special characters

        # First mock for UTF-8 decode error, then Latin-1 success
        with patch("aiofiles.open") as mock_file:
            # First call raises UnicodeDecodeError, second succeeds with Latin-1
            mock_file.side_effect = [
                mock_open(read_data=test_content).return_value,  # UTF-8 attempt
                mock_open(read_data=test_content).return_value,  # Latin-1 attempt
            ]

            # Make the first mock raise UnicodeDecodeError
            mock_file.return_value.__aenter__.side_effect = UnicodeDecodeError(
                "utf-8", b"", 0, 1, "codec can't decode"
            )

            result = await extract_text_metadata(Path("/fake/path/test.txt"))

            assert result["encoding"] in ["latin-1", "binary"]

    @pytest.mark.asyncio
    async def test_extract_text_metadata_binary_file(self):
        """Test extracting metadata from binary file."""
        # Binary content that can't be decoded
        test_content = b"\x00\x01\x02\x03\xff\xfe"  # Binary data

        with patch("aiofiles.open", mock_open(read_data=test_content)):
            # Mock will raise exceptions for both encodings
            with patch("builtins.open") as mock_builtins:
                mock_builtins.side_effect = Exception("Can't decode")

                result = await extract_text_metadata(Path("/fake/path/binary.bin"))
                assert result["encoding"] == "binary"


class TestExtractPdfMetadata:
    """Test cases for extract_pdf_metadata function."""

    @pytest.mark.asyncio
    async def test_extract_pdf_metadata_success(self):
        """Test successful PDF metadata extraction."""
        with patch("pydocs.schema.file.PdfReader") as mock_pdf_reader:
            # Mock PDF reader and pages
            mock_reader = AsyncMock()
            mock_pdf_reader.return_value = mock_reader

            mock_page = AsyncMock()
            mock_page.extract_text.return_value = "Page content"

            mock_reader.pages = [mock_page]
            mock_reader.is_encrypted = False
            mock_reader.pdf_header = "%PDF-1.4"
            mock_reader.metadata = {
                "/Title": "Test PDF",
                "/Author": "Test Author",
                "/Subject": "Test Subject",
            }

            result = await extract_pdf_metadata(Path("/fake/path/test.pdf"))

            assert result["page_count"] == 1
            assert result["is_encrypted"] is False
            assert result["pdf_version"] == "1.4"
            assert result["pdf_title"] == "Test PDF"
            assert result["is_searchable"] is True

    @pytest.mark.asyncio
    async def test_extract_pdf_metadata_encrypted(self):
        """Test PDF metadata extraction for encrypted PDF."""
        with patch("pydocs.schema.file.PdfReader") as mock_pdf_reader:
            # Mock PDF reader and pages
            mock_reader = AsyncMock()
            mock_pdf_reader.return_value = mock_reader

            mock_reader.is_encrypted = True
            mock_reader.pages = []
            mock_reader.metadata = None

            result = await extract_pdf_metadata(Path("/fake/path/encrypted.pdf"))

            assert result["is_encrypted"] is True

    @pytest.mark.asyncio
    async def test_extract_pdf_metadata_import_error(self):
        """Test PDF metadata extraction when PyPDF2 is not available."""
        with patch("pydocs.schema.file.PdfReader") as mock_pdf_reader:
            # Simulate ImportError
            mock_pdf_reader.side_effect = ImportError("PyPDF2 not installed")

            result = await extract_pdf_metadata(Path("/fake/path/test.pdf"))

            assert result["page_count"] is None
            assert result["is_encrypted"] is False
            assert result["is_searchable"] is True
