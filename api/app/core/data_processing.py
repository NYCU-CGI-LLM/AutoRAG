import logging
import os
from autorag.parser import Parser
from autorag.chunker import Chunker

logger = logging.getLogger(__name__)

# Determine the default YAML path for parser
_DEFAULT_PARSER_YAML_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "simple_parse.yaml")
)

# Determine the default YAML path for chunker
_DEFAULT_CHUNKER_YAML_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "simple_chunk.yaml")
)

def run_parser_start_parsing(data_path_glob, save_dir, all_files: bool = True, yaml_path: str = _DEFAULT_PARSER_YAML_PATH):
    # Internally, AutoRAG's Parser class uses 'project_dir' to know where to save its output (e.g., a 'data' subfolder).
    parser = Parser(data_path_glob=data_path_glob, project_dir=save_dir)
    logger.info(
        f"Parser started with data_path_glob: {data_path_glob}, save_dir: {save_dir}, using yaml_path: {yaml_path}"
    )
    parser.start_parsing(yaml_path, all_files=all_files)
    logger.info("Parser completed")


def run_chunker_start_chunking(raw_path, save_dir, yaml_path: str = _DEFAULT_CHUNKER_YAML_PATH):
    # Internally, AutoRAG's Chunker class uses 'project_dir' for its operations.
    chunker = Chunker.from_parquet(raw_path, project_dir=save_dir)
    logger.info(f"Chunker initialized for raw_path: {raw_path}, save_dir: {save_dir}")
    chunker.start_chunking(yaml_path)
    logger.info(f"Chunking completed using yaml_path: {yaml_path} within save_dir: {save_dir}") 
