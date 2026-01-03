import asyncio
import hashlib
import os
import uuid
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pydocs.config import settings
from pydocs.database import get_db, current_active_user
from pydocs.models import (
    Document,
    TextDocument,
    PDFDocument,
    DocumentType,
    DocumentStatus,
    DocumentVersion,
    User,
    Tag,
    Author,
)
from pydocs.workflows import trigger_document_tagging

router = APIRouter(prefix="/files", tags=["files"])


# ============================================================================
# Pydantic Schemas for Request/Response
# ============================================================================


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""

    id: uuid.UUID
    title: str
    file_name: str
    file_size: int
    mime_type: str
    document_type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentDetailResponse(BaseModel):
    """Detailed response model for document retrieval."""

    id: uuid.UUID
    title: str
    description: Optional[str]
    file_name: str
    file_size: int
    mime_type: str
    document_type: str
    status: str
    is_public: bool
    download_count: int
    created_at: datetime
    updated_at: datetime
    checksum: Optional[str]

    # Type-specific fields
    page_count: Optional[int] = None  # PDF
    line_count: Optional[int] = None  # Text
    word_count: Optional[int] = None  # Text

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response model for document listing."""

    documents: List[DocumentDetailResponse]
    total: int
    page: int
    page_size: int


class DocumentUpdateRequest(BaseModel):
    """Request model for updating document metadata."""

    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    status: Optional[DocumentStatus] = None
    is_public: Optional[bool] = None


# ============================================================================
# Helper Functions
# ============================================================================


def get_document_type_from_mime(mime_type: str, filename: str) -> DocumentType:
    """Determine document type from MIME type and filename."""
    extension = Path(filename).suffix.lower()

    if mime_type == "application/pdf" or extension == ".pdf":
        return DocumentType.PDF
    elif mime_type == "text/markdown" or extension == ".md":
        return DocumentType.MARKDOWN
    elif mime_type == "text/html" or extension in {".html", ".htm"}:
        return DocumentType.HTML
    else:
        return DocumentType.TEXT


async def compute_file_checksum(file_path: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    async with aiofiles.open(file_path, "rb") as f:
        while chunk := await f.read(8192):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


async def save_upload_file(
    upload_file: UploadFile,
    owner_id: uuid.UUID,
) -> tuple[Path, int, str]:
    """
    Save uploaded file to disk with proper organization.
    Returns: (file_path, file_size, checksum)
    """
    # Create upload directory structure: uploads/{owner_id}/{date}/
    date_folder = datetime.utcnow().strftime("%Y/%m")
    upload_dir = settings.UPLOAD_DIR / str(owner_id) / date_folder
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename to prevent collisions
    file_extension = Path(upload_file.filename or "file").suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / unique_filename

    # Stream file to disk and compute checksum simultaneously
    sha256_hash = hashlib.sha256()
    file_size = 0

    async with aiofiles.open(file_path, "wb") as out_file:
        while chunk := await upload_file.read(8192):
            file_size += len(chunk)

            # Check size limit during upload
            if file_size > settings.MAX_UPLOAD_SIZE:
                await out_file.close()
                os.unlink(file_path)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / (1024 * 1024):.0f}MB",
                )

            sha256_hash.update(chunk)
            await out_file.write(chunk)

    return file_path, file_size, sha256_hash.hexdigest()


def validate_file(upload_file: UploadFile) -> None:
    """Validate uploaded file before processing."""
    if not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Validate extension
    extension = Path(upload_file.filename).suffix.lower()
    if extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{extension}' not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    # Validate MIME type (if provided)
    if (
        upload_file.content_type
        and upload_file.content_type not in settings.ALLOWED_MIME_TYPES
    ):
        # Allow if extension is valid (MIME types can be unreliable)
        pass


async def extract_text_metadata(file_path: Path) -> dict:
    """Extract metadata from text files."""
    try:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            content = await f.read()

        lines = content.split("\n")
        words = content.split()

        return {
            "line_count": len(lines),
            "word_count": len(words),
            "character_count": len(content),
            "content_preview": content[:2000] if content else None,
            "encoding": "utf-8",
        }
    except UnicodeDecodeError:
        # Try with latin-1 as fallback
        try:
            async with aiofiles.open(file_path, "r", encoding="latin-1") as f:
                content = await f.read()

            lines = content.split("\n")
            words = content.split()

            return {
                "line_count": len(lines),
                "word_count": len(words),
                "character_count": len(content),
                "content_preview": content[:2000] if content else None,
                "encoding": "latin-1",
            }
        except Exception:
            return {"encoding": "binary"}
    except Exception:
        return {}


async def extract_pdf_metadata(file_path: Path) -> dict:
    """
    Extract metadata and text content from PDF files using PyPDF2.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        # Fallback if PyPDF2 is not available
        return {
            "page_count": None,
            "is_encrypted": False,
            "is_searchable": True,
        }

    try:
        reader = PdfReader(file_path)

        # Extract basic metadata
        metadata = {
            "page_count": len(reader.pages),
            "is_encrypted": reader.is_encrypted,
            "pdf_version": reader.pdf_header.replace("%PDF-", "")
            if reader.pdf_header
            else None,
        }

        # Extract document metadata
        if reader.metadata:
            metadata.update(
                {
                    "pdf_title": reader.metadata.get("Title"),
                    "pdf_author": reader.metadata.get("Author"),
                    "pdf_subject": reader.metadata.get("Subject"),
                    "pdf_creator": reader.metadata.get("Creator"),
                    "pdf_producer": reader.metadata.get("Producer"),
                    "creation_date": reader.metadata.get("CreationDate"),
                    "modification_date": reader.metadata.get("ModDate"),
                }
            )

        # Extract text content for searchability
        text_content = []
        is_searchable = False

        for page in reader.pages:
            try:
                text = page.extract_text()
                if text.strip():  # Check if page has text content
                    is_searchable = True
                    text_content.append(text)
            except Exception:
                # Skip pages that can't be processed
                continue

        metadata["is_searchable"] = is_searchable

        # Store a preview of the extracted text (first 2000 characters)
        full_text = "\n".join(text_content)
        metadata["text_preview"] = full_text[:2000] if full_text else None

        return metadata
    except Exception as e:
        # Return default values if extraction fails
        return {
            "page_count": None,
            "is_encrypted": False,
            "is_searchable": True,
        }


# ============================================================================
# API Endpoints
# ============================================================================


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    title: Optional[str] = Query(
        None, description="Document title (defaults to filename)"
    ),
    description: Optional[str] = Query(None, description="Document description"),
    is_public: bool = Query(
        False, description="Whether the document is publicly accessible"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Upload a new document.

    Supported file types: .txt, .pdf, .md, .html
    Maximum file size: 50MB (configurable)
    """
    # Validate file
    validate_file(file)

    # Determine document type
    mime_type = file.content_type or "application/octet-stream"
    doc_type = get_document_type_from_mime(mime_type, file.filename or "")

    # Save file to disk
    file_path, file_size, checksum = await save_upload_file(file, current_user.id)

    try:
        # Create appropriate document model based on type
        doc_title = title or Path(file.filename or "Untitled").stem

        common_attrs = {
            "title": doc_title,
            "description": description,
            "document_type": doc_type,
            "status": DocumentStatus.DRAFT,
            "file_path": str(file_path),
            "file_name": file.filename,
            "file_size": file_size,
            "mime_type": mime_type,
            "checksum": checksum,
            "is_public": is_public,
            "owner_id": current_user.id,
        }

        # Initialize variables for content preview
        content_preview = None

        if doc_type == DocumentType.PDF:
            # Extract PDF-specific metadata
            pdf_metadata = await extract_pdf_metadata(file_path)
            content_preview = pdf_metadata.get("text_preview")
            document = PDFDocument(
                **common_attrs,
                **pdf_metadata,
            )
        else:
            # Text-based document (TEXT, MARKDOWN, HTML)
            text_metadata = await extract_text_metadata(file_path)
            content_preview = text_metadata.get("content_preview")
            document = TextDocument(
                **common_attrs,
                **text_metadata,
            )

        db.add(document)
        await db.commit()
        await db.refresh(document)

        # Trigger document tagging workflow asynchronously
        # We don't await this as it should run in the background
        asyncio.create_task(
            trigger_document_tagging(
                document_id=document.id,
                document_title=document.title,
                document_content=content_preview,
            )
        )

        return DocumentUploadResponse(
            id=document.id,
            title=document.title,
            file_name=document.file_name,
            file_size=document.file_size,
            mime_type=document.mime_type,
            document_type=document.document_type.value,
            status=document.status.value,
            created_at=document.created_at,
        )

    except Exception as e:
        # Clean up file on database error
        if file_path.exists():
            os.unlink(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save document: {str(e)}",
        )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[DocumentStatus] = Query(
        None, description="Filter by status"
    ),
    type_filter: Optional[DocumentType] = Query(
        None, description="Filter by document type"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    List documents owned by the current user with pagination and filtering.
    """
    # Build query
    query = select(Document).where(Document.owner_id == current_user.id)

    if status_filter:
        query = query.where(Document.status == status_filter)
    if type_filter:
        query = query.where(Document.document_type == type_filter)

    # Get total count
    count_result = await db.execute(
        select(Document.id).where(Document.owner_id == current_user.id)
    )
    total = len(count_result.all())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Document.created_at.desc())

    result = await db.execute(query)
    documents = result.scalars().all()

    # Build response
    doc_responses = []
    for doc in documents:
        response_data = {
            "id": doc.id,
            "title": doc.title,
            "description": doc.description,
            "file_name": doc.file_name,
            "file_size": doc.file_size,
            "mime_type": doc.mime_type,
            "document_type": doc.document_type.value,
            "status": doc.status.value,
            "is_public": doc.is_public,
            "download_count": doc.download_count,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "checksum": doc.checksum,
        }

        # Add type-specific fields
        if isinstance(doc, PDFDocument):
            response_data["page_count"] = doc.page_count
        elif isinstance(doc, TextDocument):
            response_data["line_count"] = doc.line_count
            response_data["word_count"] = doc.word_count

        doc_responses.append(DocumentDetailResponse(**response_data))

    return DocumentListResponse(
        documents=doc_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Get document details by ID.
    """
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.tags), selectinload(Document.authors))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check access
    if document.owner_id != current_user.id and not document.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    response_data = {
        "id": document.id,
        "title": document.title,
        "description": document.description,
        "file_name": document.file_name,
        "file_size": document.file_size,
        "mime_type": document.mime_type,
        "document_type": document.document_type.value,
        "status": document.status.value,
        "is_public": document.is_public,
        "download_count": document.download_count,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "checksum": document.checksum,
    }

    if isinstance(document, PDFDocument):
        response_data["page_count"] = document.page_count
    elif isinstance(document, TextDocument):
        response_data["line_count"] = document.line_count
        response_data["word_count"] = document.word_count

    return DocumentDetailResponse(**response_data)


@router.patch("/{document_id}", response_model=DocumentDetailResponse)
async def update_document(
    document_id: uuid.UUID,
    update_data: DocumentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Update document metadata.
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(document, field, value)

    await db.commit()
    await db.refresh(document)

    response_data = {
        "id": document.id,
        "title": document.title,
        "description": document.description,
        "file_name": document.file_name,
        "file_size": document.file_size,
        "mime_type": document.mime_type,
        "document_type": document.document_type.value,
        "status": document.status.value,
        "is_public": document.is_public,
        "download_count": document.download_count,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "checksum": document.checksum,
    }

    if isinstance(document, PDFDocument):
        response_data["page_count"] = document.page_count
    elif isinstance(document, TextDocument):
        response_data["line_count"] = document.line_count
        response_data["word_count"] = document.word_count

    return DocumentDetailResponse(**response_data)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Delete a document and its file.
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Delete file from disk
    file_path = Path(document.file_path)
    if file_path.exists():
        os.unlink(file_path)

    # Delete from database
    await db.delete(document)
    await db.commit()

    return None


@router.post("/{document_id}/version", response_model=DocumentUploadResponse)
async def upload_new_version(
    document_id: uuid.UUID,
    file: UploadFile = File(..., description="New version of the document"),
    change_summary: Optional[str] = Query(None, description="Summary of changes"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Upload a new version of an existing document.
    """
    # Get existing document
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.versions))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Validate file
    validate_file(file)

    # Calculate next version number
    current_versions = document.versions
    next_version = max([v.version_number for v in current_versions], default=0) + 1

    # Create version record for current state before updating
    version = DocumentVersion(
        document_id=document.id,
        version_number=next_version - 1 if next_version > 1 else 1,
        file_path=document.file_path,
        file_size=document.file_size,
        checksum=document.checksum or "",
        change_summary=change_summary,
        created_by_id=current_user.id,
    )
    db.add(version)

    # Save new file
    file_path, file_size, checksum = await save_upload_file(file, current_user.id)

    # Update document with new file info
    document.file_path = str(file_path)
    document.file_name = file.filename or document.file_name
    document.file_size = file_size
    document.checksum = checksum
    document.mime_type = file.content_type or document.mime_type

    # Update type-specific metadata
    if isinstance(document, TextDocument):
        text_metadata = await extract_text_metadata(file_path)
        for key, value in text_metadata.items():
            if hasattr(document, key):
                setattr(document, key, value)
    elif isinstance(document, PDFDocument):
        pdf_metadata = await extract_pdf_metadata(file_path)
        for key, value in pdf_metadata.items():
            if hasattr(document, key):
                setattr(document, key, value)

    await db.commit()
    await db.refresh(document)

    return DocumentUploadResponse(
        id=document.id,
        title=document.title,
        file_name=document.file_name,
        file_size=document.file_size,
        mime_type=document.mime_type,
        document_type=document.document_type.value,
        status=document.status.value,
        created_at=document.created_at,
    )
