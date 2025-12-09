# Tests

This directory contains comprehensive tests for the PyDocs application.

## Structure

```
tests/
├── conftest.py          # Shared test configurations and fixtures
├── pytest.ini           # Pytest configuration
├── test_main.py         # Tests for the main application
├── test_config.py       # Tests for application configuration
├── test_database.py     # Tests for database operations
├── test_models.py       # Tests for data models
├── api/                 # API endpoint tests
│   ├── test_files.py    # Tests for file/document endpoints
│   └── test_users.py    # Tests for user endpoints
└── unit/                # Unit tests for individual functions
    └── test_file_helpers.py  # Tests for file helper functions
```

## Running Tests

To run all tests:

```bash
pytest
```

To run tests with coverage:

```bash
pytest --cov=src/pydocs --cov-report=html
```

To run specific test categories:

```bash
# Run only unit tests
pytest -m unit

# Run only API tests
pytest -m api

# Run tests in a specific file
pytest tests/api/test_files.py

# Run a specific test class
pytest tests/api/test_files.py::TestFileUpload

# Run a specific test method
pytest tests/api/test_files.py::TestFileUpload::test_upload_document_success
```

## Test Categories

### Unit Tests (`unit/`)
- Test individual functions and helper methods
- Focus on business logic and data processing
- Fast execution, no external dependencies

### API Tests (`api/`)
- Test HTTP endpoints and request/response handling
- Use FastAPI's TestClient for isolated testing
- Mock external dependencies like databases

### Integration Tests
- Test interactions between multiple components
- May require external services (databases, etc.)

## Fixtures

Common fixtures are defined in `conftest.py`:

- `app`: FastAPI application instance
- `client`: TestClient for making HTTP requests
- `db_session`: Database session for testing
- `mock_user`: Mock regular user
- `mock_admin_user`: Mock admin user
- `mock_document`: Mock document

## Writing New Tests

1. Place unit tests in the `unit/` directory
2. Place API endpoint tests in the `api/` directory
3. Use appropriate fixtures for common objects
4. Mock external dependencies
5. Follow the existing naming conventions
6. Add meaningful assertions and error checking

## Mocking Strategy

- Use `unittest.mock` for mocking objects and functions
- Use `pytest-mock` for more advanced mocking scenarios
- Mock database operations to avoid external dependencies
- Mock file system operations when testing file handling