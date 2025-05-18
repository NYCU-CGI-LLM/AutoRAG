import os
import logging
import pathlib

from celery import shared_task
from dotenv import load_dotenv

from app.core.data_processing import (
    run_parser_start_parsing,
    run_chunker_start_chunking,
    _DEFAULT_PARSER_YAML_PATH,
    _DEFAULT_CHUNKER_YAML_PATH,
)

logger = logging.getLogger(__name__)

# Determine ROOT_DIR and ENV for loading .env files, similar to trial_tasks.py
ROOT_DIR = pathlib.PurePath(os.path.dirname(os.path.realpath(__file__))).parent.parent
ENV = os.getenv("AUTORAG_API_ENV", "dev")
ENV_FILEPATH = os.path.join(ROOT_DIR, f".env.{ENV}")

# WORK_DIR setup, similar to trial_tasks.py
if "AUTORAG_WORK_DIR" in os.environ:
    WORK_DIR = os.getenv("AUTORAG_WORK_DIR")
else:
    WORK_DIR = os.path.join(ROOT_DIR, "projects")


@shared_task(bind=True)
def parse_data_task(
    self,
    project_id: str,
    data_path_glob: str,
    target_variation_output_dir: str,
    parser_yaml_path: str = _DEFAULT_PARSER_YAML_PATH,
    all_files: bool = True,
):
    """
    Celery task to parse data for a specific variation.
    The parser will create its own 'data' subdirectory within target_variation_output_dir.
    """
    load_dotenv(ENV_FILEPATH)
    # project_work_dir = os.path.join(WORK_DIR, project_id) # May not be needed if target_variation_output_dir is absolute
    # parser_output_dir = os.path.join(project_work_dir, "parsed_data") # Old way

    # Ensure the specific variation output directory exists (it should be created by the API endpoint before calling the task)
    # However, the task can ensure it for robustness, especially the parent if target_variation_output_dir includes subfolders not yet made.
    # For now, assume target_variation_output_dir itself is the direct save_dir for the parser.
    os.makedirs(target_variation_output_dir, exist_ok=True)

    try:
        logger.info(f"Task {self.request.id}: Starting parsing for project_id {project_id}, variation output to {target_variation_output_dir} with glob {data_path_glob}")
        run_parser_start_parsing(
            data_path_glob=data_path_glob,
            save_dir=target_variation_output_dir,  # Parser will create its 'data' subfolder here
            all_files=all_files,
            yaml_path=parser_yaml_path,
        )
        logger.info(f"Task {self.request.id}: Parsing completed. Output in data subfolder of {target_variation_output_dir}")

        # Determine the path to the generated parquet file for the chunker
        # AutoRAG parser typically saves output to a 'data' subdirectory within the save_dir.
        parsed_data_subfolder = os.path.join(target_variation_output_dir, "data")
        parquet_files = list(pathlib.Path(parsed_data_subfolder).glob("*.parquet"))
        if not parquet_files:
            error_msg = f"Task {self.request.id}: No parquet files found in {parsed_data_subfolder} after parsing."
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        parsed_file_path = str(parquet_files[0])
        logger.info(f"Task {self.request.id}: Parsed file for next stage: {parsed_file_path}")

        return {
            "status": "success",
            "parser_variation_output_dir": target_variation_output_dir, # The dir passed as input
            "parsed_file_path": parsed_file_path # The specific .parquet file path
        }
    except Exception as e:
        logger.error(f"Task {self.request.id}: Error in parse_data_task for output {target_variation_output_dir}: {str(e)}", exc_info=True)
        raise


@shared_task(bind=True)
def chunk_data_task(
    self,
    project_id: str,
    parsed_file_path: str, # This comes from the output of parse_data_task
    chunker_yaml_path: str = _DEFAULT_CHUNKER_YAML_PATH,
):
    """
    Celery task to chunk data from a parsed file.
    """
    load_dotenv(ENV_FILEPATH)
    project_work_dir = os.path.join(WORK_DIR, project_id)
    # Define a specific output dir for chunker, e.g., project_id/chunked_data
    chunker_output_dir = os.path.join(project_work_dir, "chunked_data")
    os.makedirs(chunker_output_dir, exist_ok=True)

    try:
        logger.info(f"Task {self.request.id}: Starting chunking for project {project_id} with parsed_file_path {parsed_file_path}")
        run_chunker_start_chunking(
            raw_path=parsed_file_path,
            save_dir=chunker_output_dir, # Chunker will use this as its project_dir
            yaml_path=chunker_yaml_path,
        )
        logger.info(f"Task {self.request.id}: Chunking completed for project {project_id}. Output at {chunker_output_dir}")
        return {
            "status": "success",
            "chunker_output_dir": chunker_output_dir
        }
    except Exception as e:
        logger.error(f"Task {self.request.id}: Error in chunk_data_task for project {project_id}: {str(e)}", exc_info=True)
        raise
