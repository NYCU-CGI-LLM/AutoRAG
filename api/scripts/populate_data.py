#!/usr/bin/env python3
"""
Data population script for parser, chunker, and indexer tables
"""

import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(api_dir))

from app.core.database import engine
from app.models.parser import Parser, ParserStatus
from app.models.chunker import Chunker, ChunkerStatus
from app.models.indexer import Indexer, IndexerStatus
from sqlmodel import select, Session


def populate_parsers():
    """Populate parser table with common parser configurations"""
    parsers_data = [
        {
            "name": "pdf_pdfminer_v1",
            "module_type": "langchain_parse",
            "supported_mime": ["application/pdf"],
            "params": {
                "file_type": "pdf",
                "parse_method": "pdfminer"
            },
            "status": ParserStatus.ACTIVE
        },
        {
            "name": "pdf_pymupdf_v1",
            "module_type": "langchain_parse",
            "supported_mime": ["application/pdf"],
            "params": {
                "file_type": "pdf",
                "parse_method": "pymupdf"
            },
            "status": ParserStatus.ACTIVE
        },
        {
            "name": "pdf_pdfplumber_v1",
            "module_type": "langchain_parse",
            "supported_mime": ["application/pdf"],
            "params": {
                "file_type": "pdf",
                "parse_method": "pdfplumber"
            },
            "status": ParserStatus.ACTIVE
        },
        {
            "name": "pdf_llama_parse_v1",
            "module_type": "llamaparse",
            "supported_mime": ["application/pdf"],
            "params": {
                "file_type": "all_files",
                "result_type": "markdown",
                "language": "en"
            },
            "status": ParserStatus.DRAFT
        },
        {
            "name": "csv_langchain_v1",
            "module_type": "langchain_parse",
            "supported_mime": ["text/csv"],
            "params": {
                "file_type": "csv",
                "parse_method": "csv"
            },
            "status": ParserStatus.ACTIVE
        },
        {
            "name": "json_langchain_v1",
            "module_type": "langchain_parse",
            "supported_mime": ["application/json"],
            "params": {
                "file_type": "json",
                "parse_method": "json",
                "jq_schema": ".content"
            },
            "status": ParserStatus.ACTIVE
        },
        {
            "name": "markdown_unstructured_v1",
            "module_type": "langchain_parse",
            "supported_mime": ["text/markdown"],
            "params": {
                "file_type": "md",
                "parse_method": "unstructuredmarkdown"
            },
            "status": ParserStatus.ACTIVE
        },
        {
            "name": "html_bshtml_v1",
            "module_type": "langchain_parse",
            "supported_mime": ["text/html"],
            "params": {
                "file_type": "html",
                "parse_method": "bshtml"
            },
            "status": ParserStatus.ACTIVE
        },
        {
            "name": "xml_unstructured_v1",
            "module_type": "langchain_parse",
            "supported_mime": ["application/xml", "text/xml"],
            "params": {
                "file_type": "xml",
                "parse_method": "unstructuredxml"
            },
            "status": ParserStatus.ACTIVE
        },
        {
            "name": "all_files_directory_v1",
            "module_type": "langchain_parse",
            "supported_mime": ["*/*"],
            "params": {
                "file_type": "all_files",
                "parse_method": "directory"
            },
            "status": ParserStatus.ACTIVE
        },
        {
            "name": "all_files_unstructured_v1",
            "module_type": "langchain_parse",
            "supported_mime": ["*/*"],
            "params": {
                "file_type": "all_files",
                "parse_method": "unstructured"
            },
            "status": ParserStatus.ACTIVE
        },
        {
            "name": "all_files_upstage_v1",
            "module_type": "langchain_parse",
            "supported_mime": ["*/*"],
            "params": {
                "file_type": "all_files",
                "parse_method": "upstagedocumentparse"
            },
            "status": ParserStatus.ACTIVE
        },
        {
            "name": "ocr_clova_v1",
            "module_type": "clova",
            "supported_mime": ["image/jpeg", "image/png", "image/tiff", "application/pdf"],
            "params": {
                "file_type": "all_files",
                "table_detection": True
            },
            "status": ParserStatus.DRAFT
        }
    ]
    
    with Session(engine) as session:
        for parser_data in parsers_data:
            # Check if parser already exists
            existing = session.exec(
                select(Parser).where(Parser.name == parser_data["name"])
            ).first()
            
            if not existing:
                parser = Parser(**parser_data)
                session.add(parser)
                print(f"Added parser: {parser_data['name']}")
            else:
                print(f"Parser already exists: {parser_data['name']}")
        
        session.commit()
        print("Parser data population completed!")


def populate_chunkers():
    """Populate chunker table with common chunker configurations"""
    chunkers_data = [
        {
            "name": "token_chunker_512",
            "module_type": "llama_index_chunk",
            "chunk_method": "Token",
            "chunk_size": 512,
            "chunk_overlap": 24,
            "params": {},
            "status": ChunkerStatus.ACTIVE
        },
        {
            "name": "token_chunker_1024",
            "module_type": "llama_index_chunk",
            "chunk_method": "Token",
            "chunk_size": 1024,
            "chunk_overlap": 24,
            "params": {},
            "status": ChunkerStatus.ACTIVE
        },
        {
            "name": "sentence_chunker_v1",
            "module_type": "llama_index_chunk",
            "chunk_method": "Sentence",
            "chunk_size": 1024,
            "chunk_overlap": 24,
            "params": {},
            "status": ChunkerStatus.ACTIVE
        },
        {
            "name": "sentence_window_chunker",
            "module_type": "llama_index_chunk",
            "chunk_method": "SentenceWindow",
            "chunk_size": None,
            "chunk_overlap": None,
            "params": {
                "window_size": 3
            },
            "status": ChunkerStatus.ACTIVE
        },
        {
            "name": "semantic_llama_chunker",
            "module_type": "llama_index_chunk",
            "chunk_method": "Semantic_llama_index",
            "chunk_size": None,
            "chunk_overlap": None,
            "params": {
                "embed_model": "openai",
                "buffer_size": 1,
                "breakpoint_percentile_threshold": 95
            },
            "status": ChunkerStatus.ACTIVE
        },
        {
            "name": "semantic_double_merging",
            "module_type": "llama_index_chunk",
            "chunk_method": "SemanticDoubleMerging",
            "chunk_size": None,
            "chunk_overlap": None,
            "params": {},
            "status": ChunkerStatus.ACTIVE
        },
        {
            "name": "simple_file_chunker",
            "module_type": "llama_index_chunk",
            "chunk_method": "SimpleFile",
            "chunk_size": None,
            "chunk_overlap": None,
            "params": {},
            "status": ChunkerStatus.ACTIVE
        },
        {
            "name": "sentence_transformers_token",
            "module_type": "langchain_chunk",
            "chunk_method": "sentencetransformerstoken",
            "chunk_size": None,
            "chunk_overlap": None,
            "params": {},
            "status": ChunkerStatus.ACTIVE
        },
        {
            "name": "recursive_character_chunker",
            "module_type": "langchain_chunk",
            "chunk_method": "recursivecharacter",
            "chunk_size": None,
            "chunk_overlap": None,
            "params": {
                "separators": [" ", "\n"]
            },
            "status": ChunkerStatus.ACTIVE
        },
        {
            "name": "character_chunker_v1",
            "module_type": "langchain_chunk",
            "chunk_method": "character",
            "chunk_size": None,
            "chunk_overlap": None,
            "params": {
                "separator": ". "
            },
            "status": ChunkerStatus.ACTIVE
        },
        {
            "name": "konlpy_chunker",
            "module_type": "langchain_chunk",
            "chunk_method": "Konlpy",
            "chunk_size": None,
            "chunk_overlap": None,
            "params": {},
            "status": ChunkerStatus.DRAFT
        }
    ]
    
    with Session(engine) as session:
        for chunker_data in chunkers_data:
            # Check if chunker already exists
            existing = session.exec(
                select(Chunker).where(Chunker.name == chunker_data["name"])
            ).first()
            
            if not existing:
                chunker = Chunker(**chunker_data)
                session.add(chunker)
                print(f"Added chunker: {chunker_data['name']}")
            else:
                print(f"Chunker already exists: {chunker_data['name']}")
        
        session.commit()
        print("Chunker data population completed!")


def populate_indexers():
    """Populate indexer table with common indexer configurations"""
    indexers_data = [
        {
            "name": "openai_3_large_vector",
            "index_type": "vector",
            "model": "openai_embed_3_large",
            "params": {
                "dimension": 3072,
                "similarity_metric": "cosine",
                "normalize_embeddings": True,
                "batch_size": 50
            },
            "status": IndexerStatus.ACTIVE
        },
        {
            "name": "openai_3_small_vector",
            "index_type": "vector",
            "model": "openai_embed_3_small",
            "params": {
                "dimension": 1536,
                "similarity_metric": "cosine",
                "normalize_embeddings": True,
                "batch_size": 100
            },
            "status": IndexerStatus.ACTIVE
        },
        {
            "name": "bm25_english_indexer",
            "index_type": "bm25",
            "model": "english_tokenizer",
            "params": {
                "k1": 1.2,
                "b": 0.75,
                "epsilon": 0.25,
                "language": "english",
                "lowercase": True,
                "remove_stopwords": True
            },
            "status": IndexerStatus.DRAFT
        },
        {
            "name": "sentence_transformer_all_mpnet",
            "index_type": "vector",
            "model": "all-mpnet-base-v2",
            "params": {
                "dimension": 768,
                "similarity_metric": "cosine",
                "normalize_embeddings": True,
                "batch_size": 32,
                "device": "cpu"
            },
            "status": IndexerStatus.ACTIVE
        },
        {
            "name": "hybrid_vector_bm25",
            "index_type": "hybrid",
            "model": "text-embedding-ada-002+english_tokenizer",
            "params": {
                "vector_weight": 0.7,
                "bm25_weight": 0.3,
                "vector_params": {
                    "dimension": 1536,
                    "similarity_metric": "cosine"
                },
                "bm25_params": {
                    "k1": 1.2,
                    "b": 0.75
                }
            },
            "status": IndexerStatus.DRAFT
        },
        {
            "name": "cohere_embed_english_v3",
            "index_type": "vector",
            "model": "embed-english-v3.0",
            "params": {
                "dimension": 1024,
                "similarity_metric": "cosine",
                "input_type": "search_document",
                "normalize_embeddings": True,
                "batch_size": 96
            },
            "status": IndexerStatus.ACTIVE
        },
        {
            "name": "huggingface_bge_large",
            "index_type": "vector",
            "model": "BAAI/bge-large-en-v1.5",
            "params": {
                "dimension": 1024,
                "similarity_metric": "cosine",
                "normalize_embeddings": True,
                "batch_size": 16,
                "max_length": 512
            },
            "status": IndexerStatus.ACTIVE
        }
    ]
    
    with Session(engine) as session:
        for indexer_data in indexers_data:
            # Check if indexer already exists
            existing = session.exec(
                select(Indexer).where(Indexer.name == indexer_data["name"])
            ).first()
            
            if not existing:
                indexer = Indexer(**indexer_data)
                session.add(indexer)
                print(f"Added indexer: {indexer_data['name']}")
            else:
                print(f"Indexer already exists: {indexer_data['name']}")
        
        session.commit()
        print("Indexer data population completed!")


def main():
    """Main function to populate all data"""
    print("Starting data population...")
    print("=" * 50)
    
    try:
        print("\n1. Populating parsers...")
        populate_parsers()
        
        print("\n2. Populating chunkers...")
        populate_chunkers()
        
        print("\n3. Populating indexers...")
        populate_indexers()
        
        print("\n" + "=" * 50)
        print("Data population completed successfully!")
        print("\nSummary:")
        print("- Parsers: PDF, DOCX, TXT, HTML, Images, CSV, JSON")
        print("- Chunkers: Token, Character, Sentence, Recursive, Semantic, Markdown")
        print("- Indexers: OpenAI embeddings, BM25, Sentence Transformers, Hybrid, Cohere, BGE")
        
    except Exception as e:
        print(f"Error during data population: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 