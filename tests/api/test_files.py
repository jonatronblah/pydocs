import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from pydocs.models import DocumentType, DocumentStatus


class TestFileUpload:
    """Test cases for document upload endpoint."""

    def test_upload_document_success(self, client, mock_user):
        """Test successful document upload."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch("pydocs.schema.file.get_db") as mock_db,
            patch("pydocs.schema.file.save_upload_file") as mock_save,
            patch("pydocs.schema.file.extract_text_metadata") as mock_extract,
        ):
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock file saving
            mock_save.return_value = ("/fake/path/test.txt", 1024, "abc123")

            # Mock metadata extraction
            mock_extract.return_value = {
                "line_count": 10,
                "word_count": 50,
                "character_count": 300,
            }

            # Mock document creation
            mock_document = MagicMock()
            mock_document.id = uuid.uuid4()
            mock_document.title = "Test Document"
            mock_document.file_name = "test.txt"
            mock_document.file_size = 1024
            mock_document.mime_type = "text/plain"
            mock_document.document_type = DocumentType.TEXT
            mock_document.status = DocumentStatus.DRAFT
            mock_document.created_at = "2023-01-01T00:00:00"

            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            # Make request
            response = client.post(
                "/files/upload",
                files={"file": ("test.txt", b"test content", "text/plain")},
                params={
                    "title": "Test Document",
                    "description": "A test document",
                    "is_public": False,
                },
            )

            # Assertions
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["title"] == "Test Document"
            assert data["file_name"] == "test.txt"
            assert data["document_type"] == "text"
            assert data["status"] == "draft"

    def test_upload_document_without_title(self, client, mock_user):
        """Test document upload without title defaults to filename."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch("pydocs.schema.file.get_db") as mock_db,
            patch("pydocs.schema.file.save_upload_file") as mock_save,
            patch("pydocs.schema.file.extract_text_metadata") as mock_extract,
        ):
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock file saving
            mock_save.return_value = ("/fake/path/test.txt", 1024, "abc123")

            # Mock metadata extraction
            mock_extract.return_value = {
                "line_count": 10,
                "word_count": 50,
                "character_count": 300,
            }

            # Mock document creation
            mock_document = MagicMock()
            mock_document.id = uuid.uuid4()
            mock_document.title = "test"  # Should default to filename stem
            mock_document.file_name = "test.txt"
            mock_document.file_size = 1024
            mock_document.mime_type = "text/plain"
            mock_document.document_type = DocumentType.TEXT
            mock_document.status = DocumentStatus.DRAFT
            mock_document.created_at = "2023-01-01T00:00:00"

            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            # Make request without title
            response = client.post(
                "/files/upload",
                files={"file": ("test.txt", b"test content", "text/plain")},
                params={"description": "A test document", "is_public": False},
            )

            # Assertions
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["title"] == "test"  # Filename stem

    def test_upload_invalid_file_type(self, client, mock_user):
        """Test uploading an invalid file type."""
        with patch("pydocs.schema.file.current_active_user", return_value=mock_user):
            # Make request with invalid file type
            response = client.post(
                "/files/upload",
                files={
                    "file": (
                        "test.exe",
                        b"malicious content",
                        "application/octet-stream",
                    )
                },
            )

            # Assertions
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "not allowed" in data["detail"]

    def test_upload_file_too_large(self, client, mock_user):
        """Test uploading a file that's too large."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch(
                "pydocs.schema.file.save_upload_file",
                side_effect=Exception("File too large"),
            ),
        ):
            # Make request with large file
            response = client.post(
                "/files/upload",
                files={"file": ("large.txt", b"x" * 100000000, "text/plain")},  # 100MB
            )

            # Assertions
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestListDocuments:
    """Test cases for listing documents."""

    def test_list_documents_success(self, client, mock_user, mock_document):
        """Test successful document listing."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch("pydocs.schema.file.get_db") as mock_db,
        ):
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock query results
            mock_result = AsyncMock()
            mock_result.scalars().all.return_value = [mock_document]
            mock_session.execute.return_value = mock_result

            # Mock count query
            mock_count_result = AsyncMock()
            mock_count_result.all.return_value = [uuid.uuid4()]
            mock_session.execute.return_value = mock_count_result

            # Make request
            response = client.get("/files/")

            # Assertions
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "documents" in data
            assert data["total"] >= 0
            assert data["page"] == 1
            assert data["page_size"] == 20

    def test_list_documents_with_filters(self, client, mock_user, mock_document):
        """Test document listing with filters."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch("pydocs.schema.file.get_db") as mock_db,
        ):
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock query results
            mock_result = AsyncMock()
            mock_result.scalars().all.return_value = [mock_document]
            mock_session.execute.return_value = mock_result

            # Make request with filters
            response = client.get(
                "/files/",
                params={
                    "status_filter": "draft",
                    "type_filter": "text",
                    "page": 1,
                    "page_size": 10,
                },
            )

            # Assertions
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["page"] == 1
            assert data["page_size"] == 10


class TestGetDocument:
    """Test cases for getting a specific document."""

    def test_get_document_success(self, client, mock_user, mock_document):
        """Test successful document retrieval."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch("pydocs.schema.file.get_db") as mock_db,
        ):
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock query result
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_document
            mock_session.execute.return_value = mock_result

            # Make request
            response = client.get(f"/files/{mock_document.id}")

            # Assertions
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(mock_document.id)
            assert data["title"] == mock_document.title

    def test_get_nonexistent_document(self, client, mock_user):
        """Test getting a document that doesn't exist."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch("pydocs.schema.file.get_db") as mock_db,
        ):
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock query result - document not found
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            # Make request for non-existent document
            fake_id = uuid.uuid4()
            response = client.get(f"/files/{fake_id}")

            # Assertions
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_document_access_denied(self, client, mock_user, mock_document):
        """Test getting a document without proper permissions."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch("pydocs.schema.file.get_db") as mock_db,
        ):
            # Create a document owned by someone else
            other_user = MagicMock()
            other_user.id = uuid.uuid4()
            mock_document.owner_id = other_user.id
            mock_document.is_public = False

            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock query result
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_document
            mock_session.execute.return_value = mock_result

            # Make request
            response = client.get(f"/files/{mock_document.id}")

            # Assertions
            assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUpdateDocument:
    """Test cases for updating document metadata."""

    def test_update_document_success(self, client, mock_user, mock_document):
        """Test successful document update."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch("pydocs.schema.file.get_db") as mock_db,
        ):
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock query result
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_document
            mock_session.execute.return_value = mock_result

            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            # Make request to update document
            update_data = {
                "title": "Updated Title",
                "description": "Updated description",
                "is_public": True,
            }
            response = client.patch(f"/files/{mock_document.id}", json=update_data)

            # Assertions
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["title"] == "Updated Title"
            assert data["description"] == "Updated description"
            assert data["is_public"] is True

    def test_update_document_partial_fields(self, client, mock_user, mock_document):
        """Test updating only some document fields."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch("pydocs.schema.file.get_db") as mock_db,
        ):
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock query result
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_document
            mock_session.execute.return_value = mock_result

            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            # Make request to update only title
            update_data = {"title": "New Title Only"}
            response = client.patch(f"/files/{mock_document.id}", json=update_data)

            # Assertions
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["title"] == "New Title Only"

    def test_update_nonexistent_document(self, client, mock_user):
        """Test updating a document that doesn't exist."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch("pydocs.schema.file.get_db") as mock_db,
        ):
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock query result - document not found
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            # Make request to update non-existent document
            fake_id = uuid.uuid4()
            update_data = {"title": "New Title"}
            response = client.patch(f"/files/{fake_id}", json=update_data)

            # Assertions
            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteDocument:
    """Test cases for deleting documents."""

    def test_delete_document_success(self, client, mock_user, mock_document):
        """Test successful document deletion."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch("pydocs.schema.file.get_db") as mock_db,
            patch("pydocs.schema.file.os.unlink") as mock_unlink,
        ):
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock query result
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_document
            mock_session.execute.return_value = mock_result

            mock_session.delete = AsyncMock()
            mock_session.commit = AsyncMock()

            # Make request to delete document
            response = client.delete(f"/files/{mock_document.id}")

            # Assertions
            assert response.status_code == status.HTTP_204_NO_CONTENT
            mock_unlink.assert_called_once_with(mock_document.file_path)

    def test_delete_nonexistent_document(self, client, mock_user):
        """Test deleting a document that doesn't exist."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch("pydocs.schema.file.get_db") as mock_db,
        ):
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock query result - document not found
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            # Make request to delete non-existent document
            fake_id = uuid.uuid4()
            response = client.delete(f"/files/{fake_id}")

            # Assertions
            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUploadNewVersion:
    """Test cases for uploading new document versions."""

    def test_upload_new_version_success(self, client, mock_user, mock_document):
        """Test successful new version upload."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch("pydocs.schema.file.get_db") as mock_db,
            patch("pydocs.schema.file.save_upload_file") as mock_save,
            patch("pydocs.schema.file.extract_text_metadata") as mock_extract,
        ):
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock query result for existing document
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_document
            mock_session.execute.return_value = mock_result

            # Mock file saving
            mock_save.return_value = ("/fake/path/test_v2.txt", 2048, "def456")

            # Mock metadata extraction
            mock_extract.return_value = {
                "line_count": 20,
                "word_count": 100,
                "character_count": 600,
            }

            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            # Make request to upload new version
            response = client.post(
                f"/files/{mock_document.id}/version",
                files={"file": ("test_v2.txt", b"updated content", "text/plain")},
                params={"change_summary": "Added more content"},
            )

            # Assertions
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["file_name"] == "test_v2.txt"
            assert data["file_size"] == 2048

    def test_upload_new_version_nonexistent_document(self, client, mock_user):
        """Test uploading a new version for a document that doesn't exist."""
        with (
            patch("pydocs.schema.file.current_active_user", return_value=mock_user),
            patch("pydocs.schema.file.get_db") as mock_db,
        ):
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session

            # Mock query result - document not found
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            # Make request to upload new version for non-existent document
            fake_id = uuid.uuid4()
            response = client.post(
                f"/files/{fake_id}/version",
                files={"file": ("test_v2.txt", b"updated content", "text/plain")},
            )

            # Assertions
            assert response.status_code == status.HTTP_404_NOT_FOUND
