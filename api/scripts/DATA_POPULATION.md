# Data Population Script

This document explains how to use the `populate_data.py` script to automatically populate the parser, chunker, and indexer tables with common configurations.

## Location

The script is located at: `api/populate_data.py`

## Usage

### Prerequisites

1. Ensure your database is running and accessible
2. Make sure the database tables are created (run migrations if needed)
3. Set the `DATABASE_URL` environment variable if using a non-default database

### Running the Script

From the `api` directory:

```bash
# Make sure you're in the api directory
cd api

# Run the script
python populate_data.py

# Or run it directly (if executable)
./populate_data.py
```

### What the Script Does

The script populates three main tables with realistic, production-ready configurations:

#### 1. Parsers (13 configurations)
- **PDF Parsers**: PDFMiner, PyMuPDF, PDFPlumber for different PDF processing needs
- **LlamaParse**: Advanced PDF parsing with markdown output
- **Document Parsers**: CSV, JSON, Markdown, HTML, XML support
- **Universal Parsers**: Directory, Unstructured, Upstage Document Parse for all file types
- **OCR Parser**: Naver Clova OCR with table detection
- **Text Parsers**: Simple text file processing
- **Web Parsers**: HTML parsing with BeautifulSoup
- **Image Parsers**: OCR support via Tesseract
- **Data Parsers**: CSV and JSON file support

#### 2. Chunkers (11 configurations)
- **LlamaIndex Chunkers**: Token, Sentence, SentenceWindow, Semantic, SemanticDoubleMerging, SimpleFile
- **LangChain Chunkers**: SentenceTransformersToken, RecursiveCharacter, Character, Konlpy
- **Features**: File name addition, various chunk sizes, semantic understanding, Korean language support

#### 3. Indexers (7 configurations)
- **OpenAI Embeddings**: Ada-002, GPT-3 Large, GPT-3 Small
- **BM25**: Traditional keyword-based search
- **Sentence Transformers**: Open-source embedding models
- **Hybrid**: Combined vector and BM25 search
- **Cohere**: Commercial embedding service
- **BGE**: High-performance open-source embeddings

### Safety Features

- **Duplicate Prevention**: The script checks for existing entries and won't create duplicates
- **Transaction Safety**: Uses database transactions to ensure data consistency
- **Error Handling**: Graceful error handling with informative messages

### Customization

To add your own configurations:

1. Edit the `populate_data.py` script
2. Add new entries to the respective `*_data` lists in each function
3. Follow the existing data structure patterns
4. Run the script again (it will skip existing entries)

### Example Output

```
Starting data population...
==================================================

1. Populating parsers...
Added parser: pdf_pymupdf_v1
Added parser: pdf_llama_parse_v1
...
Parser data population completed!

2. Populating chunkers...
Added chunker: token_chunker_512
Added chunker: token_chunker_1024
...
Chunker data population completed!

3. Populating indexers...
Added indexer: openai_ada_002_vector
Added indexer: openai_3_large_vector
...
Indexer data population completed!

==================================================
Data population completed successfully!

Summary:
- Parsers: PDF (PDFMiner, PyMuPDF, PDFPlumber), LlamaParse, CSV, JSON, Markdown, HTML, XML, Universal parsers, OCR
- Chunkers: Token, Sentence, SentenceWindow, Semantic, SemanticDoubleMerging, SimpleFile, LangChain Chunkers
- Indexers: OpenAI embeddings, BM25, Sentence Transformers, Hybrid, Cohere, BGE
```