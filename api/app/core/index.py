import os
import argparse
import pandas as pd
import asyncio
import yaml # For loading the single config dict

# Instead of load_vectordb_from_yaml, we might need to import specific DB types
# and a way to dispatch to them.
# For now, let's assume AutoRAG provides a way to get DB classes by type string.
# This is a placeholder for actual AutoRAG DB class imports and dispatch logic.
# from autorag.vectordb import Chroma, Pinecone, ... 
# from autorag.utils.util import load_yaml_config # We'll use this directly

from autorag.nodes.retrieval.vectordb import vectordb_ingest
from autorag.utils.util import load_yaml_config # To load the single config dict
from autorag.vectordb import get_support_vectordb # Corrected import for getting DB class support

# CLI for ingesting a corpus into the configured vector database

def index_corpus(project_dir: str, corpus_path: str, vectordb_name: str = "default"):
    """
    Load the vectordb configuration from [project_dir]/resources/vectordb.yaml 
    and ingest the given parquet file.
    The vectordb.yaml is expected to have a top-level key 'vectordb' 
    which contains a list of configurations. This function will use the first configuration in that list.

    :param project_dir: Path to the project directory (e.g., index variation output dir) 
                        containing resources/vectordb.yaml
    :param corpus_path: Path to the corpus parquet file with columns 'doc_id' and 'contents'
    :param vectordb_name: The name of the original config file (e.g., "default", "vectordb"). 
                          Used for logging and potentially if the DB class needs an explicit name.
    """
    yaml_path = os.path.join(project_dir, "resources", "vectordb.yaml")
    
    full_config = load_yaml_config(yaml_path)

    if not isinstance(full_config, dict):
        raise ValueError(f"Content of {yaml_path} is not a dictionary as expected. Found: {type(full_config)}")

    config_list = full_config.get("vectordb")
    if not isinstance(config_list, list) or not config_list:
        raise ValueError(f"'{yaml_path}' must contain a top-level key 'vectordb' with a non-empty list of configurations.")

    # Use the first configuration from the list
    target_config_dict = config_list[0]

    if not isinstance(target_config_dict, dict):
        raise ValueError(f"The first item under 'vectordb' in {yaml_path} is not a dictionary.")

    # Extract the vector database type using 'db_type' key
    # Keep a mutable copy for pop
    params_for_instantiation = target_config_dict.copy()
    vectordb_type_str = params_for_instantiation.pop("db_type", None)
    if not vectordb_type_str:
        raise ValueError(f"'db_type' key not found in the selected vector DB configuration within {yaml_path}")

    # Remove 'name' key as it's not a standard constructor argument for DB classes like Chroma.
    # This key is used to identify the config block within the YAML list, not for DB instantiation.
    params_for_instantiation.pop("name", None) 

    try:
        VectordbClass = get_support_vectordb(vectordb_type_str)
    except KeyError: 
        raise ValueError(f"Unknown or unsupported vector database type: '{vectordb_type_str}' (from 'db_type') specified in {yaml_path}")
    
    try:
        if "project_dir" in VectordbClass.__init__.__code__.co_varnames:
             vectordb = VectordbClass(**params_for_instantiation, project_dir=project_dir)
        else:
             vectordb = VectordbClass(**params_for_instantiation)

    except Exception as e:
        raise RuntimeError(f"Failed to instantiate VectorDB type '{vectordb_type_str}' with params from {yaml_path}: {str(e)}")

    corpus_df = pd.read_parquet(corpus_path)
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
        help="Name of the original vectordb config file (e.g., 'default') - used for logging."
    )
    args = parser.parse_args()
    index_corpus(args.project_dir, args.corpus_path, args.vectordb_name) 