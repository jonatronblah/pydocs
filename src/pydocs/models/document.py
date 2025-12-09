from __future__ import annotations

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    ForeignKey,
    func,
    Table,
    Column,
    Text,
    Integer,
    String,
    DateTime,
    Boolean,
    Enum as SQLEnum,
)
from datetime import datetime
import uuid
import enum
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User

from .base import Base


class DocumentType(enum.Enum):
    """Document type enumeration."""

    TEXT = "text"
    PDF = "pdf"
    MARKDOWN = "markdown"
    HTML = "html"


class DocumentStatus(enum.Enum):
    """Document status enumeration."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# Association table for many-to-many relationship between documents and tags
document_tags = Table(
    "document_tags",
    Base.metadata,
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("document.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        UUID(as_uuid=True),
        ForeignKey("tag.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# Association table for document-author relationship (many-to-many)
document_authors = Table(
    "document_authors",
    Base.metadata,
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("document.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "author_id",
        UUID(as_uuid=True),
        ForeignKey("author.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Author(Base):
    """Represents a document author."""

    __tablename__ = "author"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True
    )
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
    )

    # Relationships
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        secondary=document_authors,
        back_populates="authors",
    )


class Tag(Base):
    """Represents a tag for categorizing documents."""

    __tablename__ = "tag"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(
        String(7), nullable=True
    )  # Hex color code

    # Relationships
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        secondary=document_tags,
        back_populates="tags",
    )


class Document(Base):
    """Base document model with common attributes for all document types."""

    __tablename__ = "document"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    document_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType),
        nullable=False,
        default=DocumentType.TEXT,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus),
        nullable=False,
        default=DocumentStatus.DRAFT,
    )

    # File storage info
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # Size in bytes
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    checksum: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )  # SHA-256 hash

    # Metadata
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=datetime.utcnow,
    )

    # Owner reference (the user who uploaded)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appuser.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Discriminator for single-table inheritance
    type: Mapped[str] = mapped_column(String(50))

    __mapper_args__ = {
        "polymorphic_identity": "document",
        "polymorphic_on": "type",
    }

    # Relationships
    owner: Mapped["User"] = relationship("User", backref="documents")
    authors: Mapped[List["Author"]] = relationship(
        "Author",
        secondary=document_authors,
        back_populates="documents",
    )
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary=document_tags,
        back_populates="documents",
    )
    versions: Mapped[List["DocumentVersion"]] = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="desc(DocumentVersion.version_number)",
    )


class TextDocument(Document):
    """Model for plain text documents."""

    __tablename__ = "text_document"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Text-specific attributes
    encoding: Mapped[str] = mapped_column(String(50), default="utf-8", nullable=False)
    line_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    character_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True
    )  # ISO 639-1 code

    # Full text content (for searchability, optional for large files)
    content_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "text",
    }


class PDFDocument(Document):
    """Model for PDF documents."""

    __tablename__ = "pdf_document"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # PDF-specific attributes
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pdf_version: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_searchable: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # Has text layer

    # PDF metadata extracted from the file
    pdf_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pdf_author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pdf_subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pdf_creator: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pdf_producer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    creation_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    modification_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Extracted text preview for search
    text_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "pdf",
    }


class DocumentVersion(Base):
    """Tracks document versions for version control."""

    __tablename__ = "document_version"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Version file info
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    # Version metadata
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appuser.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="versions")
    created_by: Mapped[Optional["User"]] = relationship("User")
