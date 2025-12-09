import pytest
import uuid
from datetime import datetime
from pydocs.models import (
    User,
    Document,
    TextDocument,
    PDFDocument,
    DocumentVersion,
    DocumentType,
    DocumentStatus,
    Author,
    Tag,
)


class TestUserModel:
    """Test cases for User model."""

    def test_user_creation(self):
        """Test User model creation."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )

        assert user.id == user_id
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.hashed_password == "hashed_password"

    def test_user_table_name(self):
        """Test User model table name."""
        assert User.__tablename__ == "appuser"


class TestDocumentModels:
    """Test cases for Document models."""

    def test_document_type_enum(self):
        """Test DocumentType enum values."""
        assert DocumentType.TEXT.value == "text"
        assert DocumentType.PDF.value == "pdf"
        assert DocumentType.MARKDOWN.value == "markdown"
        assert DocumentType.HTML.value == "html"

    def test_document_status_enum(self):
        """Test DocumentStatus enum values."""
        assert DocumentStatus.DRAFT.value == "draft"
        assert DocumentStatus.PUBLISHED.value == "published"
        assert DocumentStatus.ARCHIVED.value == "archived"

    def test_base_document_creation(self):
        """Test base Document model creation."""
        doc_id = uuid.uuid4()
        owner_id = uuid.uuid4()

        document = Document(
            id=doc_id,
            title="Test Document",
            description="A test document",
            document_type=DocumentType.TEXT,
            status=DocumentStatus.DRAFT,
            file_path="/fake/path/test.txt",
            file_name="test.txt",
            file_size=1024,
            mime_type="text/plain",
            checksum="abc123",
            is_public=False,
            download_count=0,
            owner_id=owner_id,
            type="document",
        )

        assert document.id == doc_id
        assert document.title == "Test Document"
        assert document.document_type == DocumentType.TEXT
        assert document.status == DocumentStatus.DRAFT
        assert document.file_size == 1024
        assert document.is_public is False

    def test_text_document_creation(self):
        """Test TextDocument model creation."""
        doc_id = uuid.uuid4()
        owner_id = uuid.uuid4()

        text_doc = TextDocument(
            id=doc_id,
            title="Test Text Document",
            document_type=DocumentType.TEXT,
            status=DocumentStatus.DRAFT,
            file_path="/fake/path/test.txt",
            file_name="test.txt",
            file_size=1024,
            mime_type="text/plain",
            owner_id=owner_id,
            type="text",
            encoding="utf-8",
            line_count=10,
            word_count=50,
            character_count=300,
        )

        assert text_doc.id == doc_id
        assert text_doc.title == "Test Text Document"
        assert text_doc.encoding == "utf-8"
        assert text_doc.line_count == 10
        assert text_doc.word_count == 50

    def test_pdf_document_creation(self):
        """Test PDFDocument model creation."""
        doc_id = uuid.uuid4()
        owner_id = uuid.uuid4()

        pdf_doc = PDFDocument(
            id=doc_id,
            title="Test PDF Document",
            document_type=DocumentType.PDF,
            status=DocumentStatus.DRAFT,
            file_path="/fake/path/test.pdf",
            file_name="test.pdf",
            file_size=2048,
            mime_type="application/pdf",
            owner_id=owner_id,
            type="pdf",
            page_count=5,
            pdf_version="1.4",
            is_encrypted=False,
            is_searchable=True,
        )

        assert pdf_doc.id == doc_id
        assert pdf_doc.title == "Test PDF Document"
        assert pdf_doc.page_count == 5
        assert pdf_doc.pdf_version == "1.4"
        assert pdf_doc.is_encrypted is False
        assert pdf_doc.is_searchable is True

    def test_document_version_creation(self):
        """Test DocumentVersion model creation."""
        version_id = uuid.uuid4()
        document_id = uuid.uuid4()
        creator_id = uuid.uuid4()

        version = DocumentVersion(
            id=version_id,
            document_id=document_id,
            version_number=2,
            file_path="/fake/path/test_v2.txt",
            file_size=1500,
            checksum="def456",
            change_summary="Added more content",
            created_by_id=creator_id,
        )

        assert version.id == version_id
        assert version.document_id == document_id
        assert version.version_number == 2
        assert version.file_size == 1500
        assert version.change_summary == "Added more content"


class TestAuthorModel:
    """Test cases for Author model."""

    def test_author_creation(self):
        """Test Author model creation."""
        author_id = uuid.uuid4()

        author = Author(
            id=author_id, name="John Doe", email="john@example.com", bio="A test author"
        )

        assert author.id == author_id
        assert author.name == "John Doe"
        assert author.email == "john@example.com"
        assert author.bio == "A test author"

    def test_author_table_name(self):
        """Test Author model table name."""
        assert Author.__tablename__ == "author"


class TestTagModel:
    """Test cases for Tag model."""

    def test_tag_creation(self):
        """Test Tag model creation."""
        tag_id = uuid.uuid4()

        tag = Tag(
            id=tag_id,
            name="Python",
            description="Python programming language",
            color="#3776ab",
        )

        assert tag.id == tag_id
        assert tag.name == "Python"
        assert tag.description == "Python programming language"
        assert tag.color == "#3776ab"

    def test_tag_table_name(self):
        """Test Tag model table name."""
        assert Tag.__tablename__ == "tag"


class TestModelRelationships:
    """Test cases for model relationships."""

    def test_document_owner_relationship(self):
        """Test Document to User (owner) relationship."""
        # This is more of a structural test since we can't easily test
        # the actual relationship without a database session
        assert hasattr(Document, "owner")
        assert hasattr(User, "documents")

    def test_document_authors_relationship(self):
        """Test Document to Author many-to-many relationship."""
        assert hasattr(Document, "authors")
        assert hasattr(Author, "documents")

    def test_document_tags_relationship(self):
        """Test Document to Tag many-to-many relationship."""
        assert hasattr(Document, "tags")
        assert hasattr(Tag, "documents")

    def test_document_versions_relationship(self):
        """Test Document to DocumentVersion one-to-many relationship."""
        assert hasattr(Document, "versions")
        assert hasattr(DocumentVersion, "document")
