# Parser Service Testing

This directory contains test scripts for the parser service implementation.

## Quick Test

Run the simple test to check if everything is working:

```bash
cd api
python tests/simple_parser_test.py
```

This will test:
- Import functionality
- AutoRAG module availability
- Database connection
- MinIO connection
- Basic parser service operations

## Comprehensive CLI Testing

For more detailed testing, use the comprehensive CLI test tool:

```bash
cd api
python tests/test_parser_service.py --help
```

### Example Usage

1. **Check AutoRAG availability:**
   ```bash
   python tests/test_parser_service.py test-autorag
   ```

2. **Create a test library:**
   ```bash
   python tests/test_parser_service.py create-library --name "My Test Library"
   ```

3. **Create a parser:**
   ```bash
   python tests/test_parser_service.py create-parser \
     --name "pdf_parser" \
     --module-type "langchain" \
     --mime-types "application/pdf" \
     --params '{"parse_method": "pymupdf"}'
   ```

4. **List all parsers:**
   ```bash
   python tests/test_parser_service.py list-parsers
   ```

5. **Upload a file:**
   ```bash
   python tests/test_parser_service.py upload-file \
     --library-id <library-uuid> \
     --file-path "/path/to/your/file.pdf"
   ```

6. **Parse a file:**
   ```bash
   python tests/test_parser_service.py parse-file \
     --file-id <file-uuid> \
     --parser-id <parser-uuid>
   ```

7. **Get parse results:**
   ```bash
   python tests/test_parser_service.py get-results --parser-id <parser-uuid>
   ```

8. **Get parsed data:**
   ```bash
   python tests/test_parser_service.py get-data --result-id <result-id>
   ```

## Prerequisites

Before running the tests, make sure:

1. **Database is running:**
   - PostgreSQL should be running
   - DATABASE_URL environment variable should be set
   - Database tables should be created

2. **MinIO is running:**
   - MinIO server should be accessible
   - MinIO credentials should be configured in environment variables

3. **AutoRAG is available:**
   - AutoRAG should be installed in the specified path
   - Required dependencies should be available

## Environment Variables

Make sure these environment variables are set:

```bash
DATABASE_URL=postgresql://admin:admin@localhost:5432/autorag_db
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=adminadmin
MINIO_SECRET_KEY=adminadmin
MINIO_SECURE=false
MINIO_BUCKET_NAME=autorag-files
SECRET_KEY=your-secret-key
```

## Troubleshooting

### Import Errors
If you get import errors, check:
- Python path is correct
- All dependencies are installed
- AutoRAG path is accessible

### Database Connection Issues
If database tests fail:
- Check if PostgreSQL is running
- Verify DATABASE_URL is correct
- Ensure database exists and is accessible

### MinIO Connection Issues
If MinIO tests fail:
- Check if MinIO server is running
- Verify MinIO credentials
- Check network connectivity

### AutoRAG Module Issues
If AutoRAG modules are not available:
- Check if AutoRAG is installed in the correct path
- Verify all AutoRAG dependencies are installed
- Check if the path in parser_service.py is correct

## Test Files

- `simple_parser_test.py`: Basic functionality test
- `test_parser_service.py`: Comprehensive CLI testing tool

Both scripts are designed to be run from the `api` directory. 