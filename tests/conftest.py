import pytest
import asyncio
import uuid
from unittest.mock import MagicMock
from typing import Generator, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from pydocs import create_app
from pydocs.database import sessionmanager
from pydocs.models import User, Document, DocumentType, DocumentStatus


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def app():
    """Create a FastAPI app for testing."""
    # Create app without initializing database connections
    app = create_app(init=False)
    yield app


@pytest.fixture
async def client(app):
    """Create a test client for the FastAPI app."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def db_session():
    """Create a database session for testing."""
    # Using an in-memory SQLite database for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)
    session_local = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        # Create all tables
        from pydocs.models.base import Base

        await conn.run_sync(Base.metadata.create_all)

    async with session_local() as session:
        yield session
        await session.close()

    await engine.dispose()


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.username = "testuser"
    user.is_active = True
    user.is_verified = True
    user.is_superuser = False
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user for testing."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "admin@example.com"
    user.username = "admin"
    user.is_active = True
    user.is_verified = True
    user.is_superuser = True
    return user


@pytest.fixture
def mock_document(mock_user):
    """Create a mock document for testing."""
    doc = MagicMock(spec=Document)
    doc.id = uuid.uuid4()
    doc.title = "Test Document"
    doc.description = "A test document"
    doc.document_type = DocumentType.TEXT
    doc.status = DocumentStatus.DRAFT
    doc.file_path = "/fake/path/test.txt"
    doc.file_name = "test.txt"
    doc.file_size = 1024
    doc.mime_type = "text/plain"
    doc.checksum = "abc123"
    doc.is_public = False
    doc.download_count = 0
    doc.owner_id = mock_user.id
    doc.owner = mock_user
    return doc
