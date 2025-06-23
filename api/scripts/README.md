# AutoRAG API Scripts

This directory contains utility scripts for managing the AutoRAG API system.

## Database Scripts

### `reset_db.py`
Resets the PostgreSQL database by dropping all tables and recreating them.

```bash
cd api
python scripts/reset_db.py
```

**What it does:**
- Drops all existing tables with CASCADE
- Recreates all tables using SQLModel metadata
- Shows summary of created tables

### `populate_data.py`
Populates the database with sample parser, chunker, and indexer configurations.

```bash
cd api
python scripts/populate_data.py
```

**What it does:**
- Adds sample parsers (PDF, CSV, JSON, etc.)
- Adds sample chunkers (Token, Sentence, Semantic, etc.)
- Adds sample indexers (OpenAI, BM25, Sentence Transformers, etc.)

### `setup_sample_benchmarks.py`
Creates sample benchmark datasets for evaluation.

```bash
cd api
python scripts/setup_sample_benchmarks.py
```

**What it does:**
- Downloads real benchmark datasets from HuggingFace (TriviaQA, MS MARCO, HotpotQA, ELI5)
- Uploads data to MinIO
- Creates benchmark dataset records in PostgreSQL
- Handles fallback to mock data if HuggingFace fails

## MinIO Scripts

### `reset_minio.py` 
**⚠️ DESTRUCTIVE OPERATION** - Deletes all MinIO buckets and recreates them.

```bash
cd api
python scripts/reset_minio.py
```

**Interactive mode:**
- Shows confirmation prompt before proceeding
- Lists all buckets that will be deleted
- Recreates all necessary buckets

**What it does:**
1. Deletes ALL existing buckets and their contents
2. Recreates these buckets:
   - `autorag-files` - Main file storage
   - `rag-benchmarks` - Evaluation benchmark datasets
   - `rag-evaluations` - Evaluation results and reports
   - `rag-chunked-files` - Document chunks after chunking
   - `rag-parsed-files` - Parsed document content
   - `rag-indexes` - Vector and search indexes

### `reset_minio_force.py`
**⚠️ DESTRUCTIVE OPERATION** - Non-interactive version of MinIO reset.

```bash
cd api
python scripts/reset_minio_force.py
```

**What it does:**
- Same as `reset_minio.py` but without confirmation prompt
- Useful for automation and CI/CD pipelines

## Complete System Reset

To completely reset both database and MinIO:

```bash
cd api

# Reset database
python scripts/reset_db.py

# Reset MinIO (interactive)
python scripts/reset_minio.py

# Populate database with sample data
python scripts/populate_data.py

# Create sample benchmark datasets
python scripts/setup_sample_benchmarks.py
```

Or use the force version for automation:

```bash
cd api

# Reset everything without prompts
python scripts/reset_db.py
python scripts/reset_minio_force.py
python scripts/populate_data.py
python scripts/setup_sample_benchmarks.py
```

## Prerequisites

- PostgreSQL database running and accessible
- MinIO server running and accessible
- All required Python dependencies installed
- Proper environment variables configured (see `.env.dev`)

## Environment Variables

Make sure these are set in your `.env.dev` file:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/autorag_db

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=adminadmin
MINIO_SECRET_KEY=adminadmin

# OpenAI (for sample benchmarks)
OPENAI_API_KEY=your-openai-api-key
```

## Safety Notes

- **Database reset** will destroy all existing data including users, libraries, files, etc.
- **MinIO reset** will delete all uploaded files, chunks, indexes, and evaluation data
- Always backup important data before running reset scripts
- Use the interactive versions in production to avoid accidental data loss
- The force versions should only be used in development/testing environments 