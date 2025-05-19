import os
import pathlib
import shutil
import tempfile
from typing import Dict, Any

import pandas as pd
from celery import shared_task
from dotenv import load_dotenv

# from autorag_cgi.api.app.db.project_db import SQLiteProjectDB
from .base import TrialTask
from autorag_cgi.api.app.schemas._schema import (
    QACreationRequest,
    Status,
)
import logging
import yaml
from src.run import (
    run_parser_start_parsing,
    run_chunker_start_chunking,
    run_qa_creation,
    run_start_trial,
    run_validate,
    run_dashboard,
    run_chat,
    run_api_server,
)

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
ROOT_DIR = pathlib.PurePath(os.path.dirname(os.path.realpath(__file__))).parent.parent
ENV = os.getenv("AUTORAG_API_ENV", "dev")

# WORK_DIR 설정
if "AUTORAG_WORK_DIR" in os.environ:
    # 환경변수로 지정된 경우 해당 경로 사용
    WORK_DIR = os.getenv("AUTORAG_WORK_DIR")
else:
    # 환경변수가 없는 경우 기본값 사용
    WORK_DIR = os.path.join(ROOT_DIR, "projects")

ENV_FILEPATH = os.path.join(ROOT_DIR, f".env.{ENV}")
if not os.path.exists(ENV_FILEPATH):
    # add empty new .env file
    with open(ENV_FILEPATH, "w") as f:
        f.write("")

load_dotenv(ENV_FILEPATH)


@shared_task(bind=True, base=TrialTask)
def chunk_documents(
    self, project_id: str, config_str: str, parse_name: str, chunk_name: str
):
    """
    Task for the chunk documents

    :param project_id: The project id of the trial
    :param config_str: Configuration string for chunking
    :param parse_name: The name of the parsed data
    :param chunk_name: The name of the chunk
    """
    load_dotenv(ENV_FILEPATH)
    parsed_data_path = os.path.join(
        WORK_DIR, project_id, "parse", parse_name, "parsed_result.parquet"
    )
    if not os.path.exists(parsed_data_path):
        raise ValueError(f"parsed_data_path does not exist: {parsed_data_path}")

    try:
        self.update_state_and_db(
            trial_id="",
            project_id=project_id,
            status="chunking",
            progress=0,
            task_type="chunk",
        )

        # 청킹 작업 수행
        logger.info("Chunking documents")

        project_dir = os.path.join(WORK_DIR, project_id)
        config_dir = os.path.join(project_dir, "config")
        chunked_data_dir = os.path.join(project_dir, "chunk", chunk_name)
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(chunked_data_dir, exist_ok=False)
    except Exception as e:
        self.update_state_and_db(
            trial_id="",
            project_id=project_id,
            status=Status.FAILED,
            progress=0,
            task_type="chunk",
            info={"error": str(e)},
        )
        raise

    try:
        # config_str을 파이썬 딕셔너리로 변환 후 다시 YAML로 저장
        if isinstance(config_str, str):
            config_dict = yaml.safe_load(config_str)
        else:
            config_dict = config_str

        # YAML 파일 형식 확인
        if "modules" not in config_dict:
            config_dict = {"modules": config_dict}

        logger.debug(f"Chunking config_dict: {config_dict}")
        # YAML 파일 저장
        yaml_path = os.path.join(config_dir, f"chunk_config_{chunk_name}.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_dict, f, allow_unicode=True)

        result = run_chunker_start_chunking(
            parsed_data_path, chunked_data_dir, yaml_path
        )

        self.update_state_and_db(
            trial_id="",
            project_id=project_id,
            status=Status.COMPLETED,
            progress=100,
            task_type="chunk",
        )
        return result
    except Exception as e:
        self.update_state_and_db(
            trial_id="",
            project_id=project_id,
            status=Status.FAILED,
            progress=0,
            task_type="chunk",
            info={"error": str(e)},
        )
        if os.path.exists(chunked_data_dir):
            os.rmdir(chunked_data_dir)
        raise


@shared_task(bind=True, base=TrialTask)
def generate_qa_documents(self, project_id: str, request_data: Dict[str, Any]):
    """
    Task for generating QA documents

    :param self: TrialTask self
    :param project_id: The project_id
    :param request_data: The request_data will be the model_dump of the QACreationRequest
    """
    load_dotenv(ENV_FILEPATH)
    qa_creation_request = QACreationRequest(**request_data)
    print(f"qa_creation_request : {qa_creation_request}")
    try:
        self.update_state_and_db(
            trial_id="",
            project_id=project_id,
            status="generating_qa_docs",
            progress=0,
            task_type="qa_docs",
        )

        # QA 생성 작업 수행
        logger.info("Generating QA documents")

        project_dir = os.path.join(WORK_DIR, project_id)
        corpus_filepath = os.path.join(
            project_dir, "chunk", qa_creation_request.chunked_name, "0.parquet"
        )
        if not os.path.exists(corpus_filepath):
            raise ValueError(f"corpus_filepath does not exist: {corpus_filepath}")

        dataset_dir = os.path.join(project_dir, "qa")

        if not os.path.exists(dataset_dir):
            os.makedirs(dataset_dir, exist_ok=False)

        run_qa_creation(qa_creation_request, corpus_filepath, dataset_dir)

        self.update_state_and_db(
            trial_id="",
            project_id=project_id,
            status=Status.COMPLETED,
            progress=100,
            task_type="qa_docs",
        )
    except Exception as e:
        self.update_state_and_db(
            trial_id="",
            project_id=project_id,
            status=Status.FAILED,
            progress=0,
            task_type="qa_docs",
            info={"error": str(e)},
        )
        raise


@shared_task(bind=True, base=TrialTask)
def parse_documents(
    self,
    project_id: str,
    config_str: str,
    parse_name: str,
    glob_path: str = "*.*",
    all_files: bool = True,
):
    load_dotenv(ENV_FILEPATH)
    try:
        self.update_state_and_db(
            trial_id="",
            project_id=project_id,
            status=Status.IN_PROGRESS,
            progress=0,
            task_type="parse",
        )

        project_dir = os.path.join(WORK_DIR, project_id)
        raw_data_path = os.path.join(project_dir, "raw_data", glob_path)
        config_dir = os.path.join(project_dir, "config")
        parsed_data_path = os.path.join(project_dir, "parse", parse_name)
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(parsed_data_path, exist_ok=False)

    except Exception as e:
        self.update_state_and_db(
            trial_id="",
            project_id=project_id,
            status=Status.FAILED,
            progress=0,
            task_type="parse",
            info={"error": str(e)},
        )
    try:
        # config_str을 파이썬 딕셔너리로 변환 후 다시 YAML로 저장
        if isinstance(config_str, str):
            config_dict = yaml.safe_load(config_str)
        else:
            config_dict = config_str

        # YAML 파일 형식 확인
        if "modules" not in config_dict:
            config_dict = {"modules": config_dict}

        # The rest of the file content would go here...
        # Due to token limits, I'm only pasting the beginning of the file.
        # Please ensure the full content is moved.

        logger.debug(f"Parsing config_dict: {config_dict}")
        # YAML 파일 저장
        yaml_path = os.path.join(config_dir, f"parse_config_{parse_name}.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_dict, f, allow_unicode=True)

        run_parser_start_parsing(
            source_data_path=raw_data_path,
            output_path=parsed_data_path,
            yaml_config_path=yaml_path,
            all_files=all_files,
        )

        self.update_state_and_db(
            trial_id="",
            project_id=project_id,
            status=Status.COMPLETED,
            progress=100,
            task_type="parse",
        )
    except Exception as e:
        self.update_state_and_db(
            trial_id="",
            project_id=project_id,
            status=Status.FAILED,
            progress=0,
            task_type="parse",
            info={"error": str(e)},
        )
        if os.path.exists(parsed_data_path):
            shutil.rmtree(parsed_data_path)
        raise


@shared_task(bind=True, base=TrialTask)
def start_validate(
    self,
    project_id: str,
    trial_id: str,
    corpus_name: str,
    qa_name: str,
    yaml_config: dict,
):
    load_dotenv(ENV_FILEPATH)
    try:
        self.update_state_and_db(
            trial_id=trial_id,
            project_id=project_id,
            status=Status.IN_PROGRESS,
            progress=0,
            task_type="validate",
        )
        project_db_path = os.path.join(WORK_DIR, project_id, "project")
        # db = SQLiteProjectDB(project_id)
        # trial = db.get_trial(trial_id)
        # if trial is None:
        #     raise ValueError(f"Trial with ID {trial_id} not found in the database.")
        # 
        # trial.status = Status.IN_PROGRESS
        # db.set_trial(trial)

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.yaml")
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(yaml_config, f)

            validate_result = run_validate(config_path, project_db_path)

            self.update_state_and_db(
                trial_id=trial_id,
                project_id=project_id,
                status=Status.COMPLETED,
                progress=100,
                task_type="validate",
            )
            # trial.status = Status.COMPLETED
            # db.set_trial(trial)
            return validate_result
    except Exception as e:
        self.update_state_and_db(
            trial_id=trial_id,
            project_id=project_id,
            status=Status.FAILED,
            progress=0,
            task_type="validate",
            info={"error": str(e)},
        )
        # if trial:
        #     trial.status = Status.FAILED
        #     db.set_trial(trial)
        raise


@shared_task(bind=True, base=TrialTask)
def start_evaluate(
    self,
    project_id: str,
    trial_id: str,
    corpus_name: str,
    qa_name: str,
    yaml_config: dict,
    project_dir: str,
    skip_validation: bool = True,
    full_ingest: bool = True,
):
    load_dotenv(ENV_FILEPATH)
    try:
        self.update_state_and_db(
            trial_id=trial_id,
            project_id=project_id,
            status=Status.IN_PROGRESS,
            progress=0,
            task_type="evaluate",
        )
        # db = SQLiteProjectDB(project_id)
        # trial = db.get_trial(trial_id)
        # if trial is None:
        #     raise ValueError(f"Trial with ID {trial_id} not found in the database.")

        # trial.status = Status.IN_PROGRESS
        # db.set_trial(trial)

        if not os.path.exists(project_dir):
            os.makedirs(project_dir)

        config_path = os.path.join(project_dir, "config.yaml")
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(yaml_config, f)

        best_result = run_start_trial(
            config_path,
            project_dir,
            skip_validation=skip_validation,
            project_dir=project_dir,
            full_ingest=full_ingest,
            corpus_name=corpus_name,
            qa_name=qa_name,
        )

        self.update_state_and_db(
            trial_id=trial_id,
            project_id=project_id,
            status=Status.COMPLETED,
            progress=100,
            task_type="evaluate",
        )
        # trial.status = Status.COMPLETED
        # db.set_trial(trial)
        return best_result
    except Exception as e:
        self.update_state_and_db(
            trial_id=trial_id,
            project_id=project_id,
            status=Status.FAILED,
            progress=0,
            task_type="evaluate",
            info={"error": str(e)},
        )
        # if trial:
        #     trial.status = Status.FAILED
        #     db.set_trial(trial)
        raise


@shared_task(bind=True, base=TrialTask)
def start_dashboard(self, project_id: str, trial_id: str, trial_dir: str):
    load_dotenv(ENV_FILEPATH)
    try:
        self.update_state_and_db(
            trial_id=trial_id,
            project_id=project_id,
            status=Status.IN_PROGRESS,
            progress=0,
            task_type="dashboard",
        )
        # db = SQLiteProjectDB(project_id)
        # trial = db.get_trial(trial_id)
        # if trial is None:
        #     raise ValueError(f"Trial with ID {trial_id} not found in the database.")

        # # PID 저장
        # trial.report_task_id = str(os.getpid())
        # db.set_trial(trial)

        result = run_dashboard(trial_dir)
        logger.info(f"Dashboard started for trial_id: {trial_id}")
        self.update_state_and_db(
            trial_id=trial_id,
            project_id=project_id,
            status=Status.COMPLETED,
            progress=100,
            task_type="dashboard",
        )
        # # PID 제거
        # trial.report_task_id = None
        # db.set_trial(trial)

        return result
    except Exception as e:
        logger.error(f"Error starting dashboard for trial {trial_id}: {str(e)}")
        self.update_state_and_db(
            trial_id=trial_id,
            project_id=project_id,
            status=Status.FAILED,
            progress=0,
            task_type="dashboard",
            info={"error": str(e)},
        )
        # if trial:
        #     trial.report_task_id = None  # 에러 발생 시 PID 제거
        #     db.set_trial(trial)
        raise


@shared_task(bind=True, base=TrialTask)
def start_chat_server(self, project_id: str, trial_id: str, trial_dir: str):
    load_dotenv(ENV_FILEPATH)
    try:
        self.update_state_and_db(
            trial_id=trial_id,
            project_id=project_id,
            status=Status.IN_PROGRESS,
            progress=0,
            task_type="chat",
        )
        # db = SQLiteProjectDB(project_id)
        # trial = db.get_trial(trial_id)
        # if trial is None:
        #     raise ValueError(f"Trial with ID {trial_id} not found in the database.")

        # # PID 저장
        # trial.chat_task_id = str(os.getpid())
        # db.set_trial(trial)

        result = run_chat(trial_dir)
        logger.info(f"Chat server started for trial_id: {trial_id}")
        self.update_state_and_db(
            trial_id=trial_id,
            project_id=project_id,
            status=Status.COMPLETED,
            progress=100,
            task_type="chat",
        )
        # # PID 제거
        # trial.chat_task_id = None
        # db.set_trial(trial)
        return result
    except Exception as e:
        logger.error(f"Error starting chat server for trial {trial_id}: {str(e)}")
        self.update_state_and_db(
            trial_id=trial_id,
            project_id=project_id,
            status=Status.FAILED,
            progress=0,
            task_type="chat",
            info={"error": str(e)},
        )
        # if trial:
        #     trial.chat_task_id = None  # 에러 발생 시 PID 제거
        #     db.set_trial(trial)
        raise


@shared_task(bind=True, base=TrialTask)
def start_api_server(self, project_id: str, trial_id: str, trial_dir: str):
    load_dotenv(ENV_FILEPATH)
    try:
        self.update_state_and_db(
            trial_id=trial_id,
            project_id=project_id,
            status=Status.IN_PROGRESS,
            progress=0,
            task_type="api",
        )
        # db = SQLiteProjectDB(project_id)
        # trial = db.get_trial(trial_id)
        # if trial is None:
        #     raise ValueError(f"Trial with ID {trial_id} not found in the database.")

        # # PID 저장
        # trial.api_pid = os.getpid()
        # db.set_trial(trial)

        result = run_api_server(trial_dir)
        logger.info(f"API server started for trial_id: {trial_id}")
        self.update_state_and_db(
            trial_id=trial_id,
            project_id=project_id,
            status=Status.COMPLETED,
            progress=100,
            task_type="api",
        )
        # # PID 제거
        # trial.api_pid = None
        # db.set_trial(trial)
        return result
    except Exception as e:
        logger.error(f"Error starting API server for trial {trial_id}: {str(e)}")
        self.update_state_and_db(
            trial_id=trial_id,
            project_id=project_id,
            status=Status.FAILED,
            progress=0,
            task_type="api",
            info={"error": str(e)},
        )
        # if trial:
        #     trial.api_pid = None  # 에러 발생 시 PID 제거
        #     db.set_trial(trial)
        raise 