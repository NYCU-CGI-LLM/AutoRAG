import os
import argparse
import pandas as pd
import asyncio

from autorag.vectordb import load_vectordb_from_yaml
from autorag.nodes.retrieval.vectordb import vectordb_ingest

# CLI for ingesting a corpus into the configured vector database

def index_corpus(project_dir: str, corpus_path: str, vectordb_name: str = "default"):
    """
    Load the vectordb configuration from resources/vectordb.yaml and ingest the given parquet file.

    :param project_dir: Path to the project directory containing resources/vectordb.yaml
    :param corpus_path: Path to the corpus parquet file with columns 'doc_id' and 'contents'
    :param vectordb_name: Name of the vectordb configuration to use (default: 'default')
    """
    yaml_path = os.path.join(project_dir, "resources", "vectordb.yaml")
    vectordb = load_vectordb_from_yaml(yaml_path, vectordb_name, project_dir)
    corpus_df = pd.read_parquet(corpus_path)
    # Run the asynchronous ingestion
    asyncio.run(vectordb_ingest(vectordb, corpus_df))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest corpus into vector database")
    parser.add_argument(
        "--project_dir", "-p", required=True,
        help="Project directory containing resources/vectordb.yaml"
    )
    parser.add_argument(
        "--corpus_path", "-c", required=True,
        help="Path to the corpus parquet file"
    )
    parser.add_argument(
        "--vectordb_name", "-v", default="default",
        help="Name of the vectordb entry in resources/vectordb.yaml"
    )
    args = parser.parse_args()
    index_corpus(args.project_dir, args.corpus_path, args.vectordb_name) 