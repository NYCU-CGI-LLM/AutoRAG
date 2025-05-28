# API Testing Guide

This directory contains comprehensive tests for the AutoRAG API service.

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── requirements-test.txt    # Testing dependencies
├── pytest.ini             # Pytest configuration
├── unit/                   # Unit tests
│   └── services/
│       └── test_parser_service_unit.py
├── integration/            # Integration tests
│   └── test_parser_integration.py
└── archived/              # Legacy tests (excluded from runs)
```

## Setup

### Install Test Dependencies

Using uv (recommended):
```bash
uv pip install -r requirements-test.txt
```

Or using the test runner:
```bash
python run_tests.py --install-deps
```

### Environment Setup

The tests use:
- **SQLite in-memory database** for fast, isolated testing
- **Mock MinIO service** to avoid external dependencies
- **Simplified table schemas** compatible with SQLite

## Running Tests

### Using the Test Runner Script

```bash
# Run all tests
python run_tests.py all

# Run only unit tests
python run_tests.py unit

# Run only integration tests
python run_tests.py integration

# Run with verbose output
python run_tests.py unit -v

# Run with coverage
python run_tests.py unit -c

# Run in parallel
python run_tests.py unit -p

# Install dependencies and run tests
python run_tests.py unit --install-deps
```

### Using pytest directly

```bash
# Run all tests
python -m pytest tests/unit/ tests/integration/

# Run specific test file
python -m pytest tests/unit/services/test_parser_service_unit.py -v

# Run specific test
python -m pytest tests/unit/services/test_parser_service_unit.py::TestParserService::test_run_autorag_parser_langchain -v

# Run with markers
python -m pytest -m unit
python -m pytest -m integration
```

## Test Categories

### Unit Tests
- Test individual functions and methods in isolation
- Use mocks for external dependencies
- Fast execution
- Located in `tests/unit/`

### Integration Tests
- Test API endpoints end-to-end
- Use test database and mock services
- Test complete workflows
- Located in `tests/integration/`

## Key Features

### Database Testing
- Uses SQLite in-memory database for speed
- Simplified schemas compatible with SQLite
- Automatic table creation and cleanup
- Isolated test sessions

### AutoRAG Parser Testing
- Mocks autorag functions (`langchain_parse`, `clova_ocr`)
- Tests parser logic without external dependencies
- Validates parameter passing and result processing

### MinIO Testing
- Mock MinIO service for file operations
- No external MinIO instance required
- Tests file upload/download workflows

## Fixtures Available

### Database Fixtures
- `test_db`: SQLite in-memory database session
- `test_settings`: Test configuration settings

### Mock Services
- `mock_minio_service`: Mocked MinIO operations

### Sample Data
- `sample_pdf_file`: Temporary PDF file for testing
- `sample_text_file`: Temporary text file for testing
- `sample_parsed_data`: Mock parsed data structure
- `sample_chunked_data`: Mock chunked data structure
- `sample_dataframe`: Pandas DataFrame for testing

### API Testing
- `client`: FastAPI test client with dependency overrides

## Writing New Tests

### Unit Test Example
```python
def test_my_function(self, parser_service, mock_dependency):
    """Test description"""
    # Arrange
    mock_dependency.return_value = "expected_result"
    
    # Act
    result = parser_service.my_function("input")
    
    # Assert
    assert result == "expected_result"
    mock_dependency.assert_called_once_with("input")
```

### Integration Test Example
```python
def test_api_endpoint(self, client, test_db):
    """Test API endpoint"""
    # Arrange
    test_data = {"key": "value"}
    
    # Act
    response = client.post("/api/v1/endpoint", json=test_data)
    
    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the `api/` directory
2. **Database Errors**: SQLite doesn't support PostgreSQL ARRAY/JSONB types - use simplified schemas
3. **Dependency Conflicts**: Use `uv pip install` for better dependency resolution

### Debugging Tests
```bash
# Run with verbose output and no capture
python -m pytest tests/unit/ -v -s

# Run specific test with debugging
python -m pytest tests/unit/services/test_parser_service_unit.py::TestParserService::test_create_parser_data -v -s --pdb
```

## CI/CD Integration

The test suite is designed to run in CI environments:
- No external dependencies required
- Fast execution (< 1 minute for full suite)
- Comprehensive coverage of core functionality
- Clear pass/fail indicators

## Contributing

When adding new tests:
1. Follow the existing naming conventions
2. Use appropriate fixtures for setup
3. Mock external dependencies
4. Add docstrings explaining test purpose
5. Use markers (`@pytest.mark.unit` or `@pytest.mark.integration`) 