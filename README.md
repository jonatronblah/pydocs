# PyDocs

PyDocs is a document management system built with FastAPI, SQLAlchemy, and PostgreSQL.

## Features

- Document upload and management
- Support for multiple file types (PDF, TXT, Markdown, HTML)
- User authentication and authorization
- Document versioning
- Metadata extraction
- Topic modeling with Gensim
- RESTful API

## Tech Stack

- **Backend**: FastAPI (Python 3.14+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: FastAPI-Users with JWT
- **File Storage**: Local file system
- **Task Queue**: Celery with Redis
- **NLP/ML**: Gensim for topic modeling
- **Frontend**: (To be implemented)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd pydocs
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Install additional NLP dependencies for topic modeling:
   ```bash
   pip install gensim nltk
   ```

4. Set up environment variables (see `.env.example`)

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

## Running the Application

```bash
# Development server
uvicorn src.main:app --reload

# Production server (using Granian)
granian --reload src.main:app
```

## Topic Modeling

To perform topic modeling on a corpus of documents:

```bash
# Using the standalone script
python src/pydocs/topic_modeling.py --input_dir <path_to_documents> --num_topics <number_of_topics>

# Example with sample documents
python src/pydocs/topic_modeling.py --input_dir sample_docs --num_topics 5 --passes 20
```

## Testing

The project includes comprehensive tests using pytest.

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src/pydocs --cov-report=html

# Run specific test categories
pytest -m unit    # Unit tests
pytest -m api     # API tests
```

For more detailed information about testing, see [tests/README.md](tests/README.md).

## Project Structure

```
src/
├── main.py              # Application entry point
├── pydocs/
│   ├── __init__.py      # App factory
│   ├── config.py        # Configuration
│   ├── database.py      # Database setup
│   ├── models/          # Database models
│   ├── schema/          # API schemas and routes
│   └── topic_modeling.py # Topic modeling script
tests/
├── api/                 # API endpoint tests
├── unit/                # Unit tests
└── conftest.py          # Test configuration
dev/
├── pdf-parsing.ipynb    # PDF parsing and topic modeling notebook
└── sample-pdfs/         # Sample PDF documents
```

## API Documentation

Once the application is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT
