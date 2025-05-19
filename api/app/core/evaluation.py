from autorag.evaluator import Evaluator
from autorag.validator import Validator


def run_start_trial(
    qa_path: str,
    corpus_path: str,
    project_dir: str,
    yaml_path: str,
    skip_validation: bool = True,
    full_ingest: bool = True,
):
    evaluator = Evaluator(qa_path, corpus_path, project_dir=project_dir)
    evaluator.start_trial(
        yaml_path, skip_validation=skip_validation, full_ingest=full_ingest
    )


def run_validate(qa_path: str, corpus_path: str, yaml_path: str):
    validator = Validator(qa_path, corpus_path)
    validator.validate(yaml_path) 