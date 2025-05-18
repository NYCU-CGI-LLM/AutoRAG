import os
import logging
import pathlib
import json
from datetime import datetime

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
    target_variation_output_dir: str, # This is where the parser saves its direct output
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
            save_dir=target_variation_output_dir,  # Parser saves here
            all_files=all_files,
            yaml_path=parser_yaml_path,
        )
        logger.info(f"Task {self.request.id}: Parsing completed. Checking output directly in {target_variation_output_dir}")

        # Log contents of the target_variation_output_dir itself
        logger.info(f"Task {self.request.id}: Checking for output in {target_variation_output_dir}")
        if os.path.exists(target_variation_output_dir):
            logger.info(f"Task {self.request.id}: Contents of {target_variation_output_dir}: {os.listdir(target_variation_output_dir)}")
        else:
            # This should not happen if the parser ran without erroring out before file creation
            logger.error(f"Task {self.request.id}: Target variation output directory {target_variation_output_dir} does not exist after parsing attempt.")
            raise FileNotFoundError(f"Target output directory {target_variation_output_dir} missing after parsing.")

        # Look for parquet files directly in target_variation_output_dir
        # The AutoRAG parser, when given save_dir, might place 'parsed_result.parquet' directly there,
        # not in a 'data' subdirectory it creates.
        parquet_files = list(pathlib.Path(target_variation_output_dir).glob("*.parquet"))
        
        if not parquet_files:
            # Construct a more informative error message, including listing files if any
            found_files_log = "No files found."
            if os.path.exists(target_variation_output_dir):
                found_files_log = f"Found files: {os.listdir(target_variation_output_dir)}"
            error_msg = f"Task {self.request.id}: No parquet files found directly in {target_variation_output_dir} after parsing. {found_files_log}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Assuming 'parsed_result.parquet' is the target, or just take the first one found.
        # If multiple parquets can exist and a specific one is needed, this logic might need refinement.
        parsed_file_path = str(parquet_files[0]) 
        logger.info(f"Task {self.request.id}: Parsed file for next stage: {parsed_file_path}")

        return {
            "status": "success",
            "parser_variation_output_dir": target_variation_output_dir,
            "parsed_file_path": parsed_file_path
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

@shared_task(bind=True)
def finalize_parsing_variation_task(self, parent_task_result: dict, *args, variation_metadata_path_str: str):
    """
    Celery task to finalize parsing variation metadata upon successful completion of parse_data_task.
    Receives the result from parse_data_task as its first argument.
    *args is used to soak up any unexpected positional arguments from Celery.
    """
    load_dotenv(ENV_FILEPATH)
    logger.info(f"Task {self.request.id}: Finalizing parsing variation. Parent task result: {parent_task_result}. Metadata file: {variation_metadata_path_str}")
    try:
        if not os.path.exists(variation_metadata_path_str):
            logger.error(f"Task {self.request.id}: Metadata file {variation_metadata_path_str} not found.")
            # Depending on desired robustness, could raise error or attempt to create default
            return {"status": "error", "message": "Metadata file not found."}

        with open(variation_metadata_path_str, 'r+') as f:
            metadata = json.load(f)
            
            metadata["status"] = "completed"
            metadata["parsed_file_path"] = parent_task_result.get("parsed_file_path")
            metadata["updated_at"] = datetime.utcnow().isoformat()
            
            f.seek(0)
            json.dump(metadata, f, indent=4)
            f.truncate()
        
        logger.info(f"Task {self.request.id}: Successfully updated metadata at {variation_metadata_path_str} to completed.")
        return {"status": "success", "updated_metadata_path": variation_metadata_path_str}
    except Exception as e:
        logger.error(f"Task {self.request.id}: Error finalizing parsing variation metadata at {variation_metadata_path_str}: {str(e)}", exc_info=True)
        # This task failing means metadata might be inconsistent. Consider retry or alerting.
        raise # Re-raise to mark the task as failed

@shared_task(bind=True)
def handle_parsing_failure_task(self, *args, variation_metadata_path_str: str):
    """
    Celery task to update parsing variation metadata upon failure of parse_data_task.
    'self' is the task instance (due to bind=True).
    *args is used to soak up any unexpected positional arguments from Celery (like exc, traceback from parent).
    Information about the failed task (like parent_id, exception) can be accessed
    via self.request if needed, or implicitly handled by Celery.
    """
    load_dotenv(ENV_FILEPATH)
    logger.info(f"Task {self.request.id}: Handling failure for parsing variation (parent task: {self.request.parent_id}). Args received: {args}. Metadata file: {variation_metadata_path_str}")
    try:
        if not os.path.exists(variation_metadata_path_str):
            logger.error(f"Task {self.request.id}: Metadata file {variation_metadata_path_str} not found during failure handling.")
            return {"status": "error", "message": "Metadata file not found during failure handling."}

        with open(variation_metadata_path_str, 'r+') as f:
            metadata = json.load(f)
            
            metadata["status"] = "failed"
            # Optionally, store error information. Be careful about storing too much (e.g., full traceback)
            # metadata["error_message"] = str(exc) 
            metadata["updated_at"] = datetime.utcnow().isoformat()
            # Clear celery_task_id or parsed_file_path if appropriate for a failed state
            metadata["parsed_file_path"] = None 
            
            f.seek(0)
            json.dump(metadata, f, indent=4)
            f.truncate()

        logger.info(f"Task {self.request.id}: Successfully updated metadata at {variation_metadata_path_str} to failed.")
        return {"status": "success", "updated_metadata_path": variation_metadata_path_str}
    except Exception as e:
        logger.error(f"Task {self.request.id}: Error updating parsing variation metadata to failed at {variation_metadata_path_str}: {str(e)}", exc_info=True)
        raise # Re-raise to mark the task as failed
