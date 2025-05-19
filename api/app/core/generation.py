import os

import pandas as pd
from autorag import generator_models
from autorag.data.qa.schema import QA

from .qa_create import default_create, fast_create, advanced_create
from app.schemas._schema import QACreationRequest


def run_qa_creation(
    qa_creation_request: QACreationRequest, corpus_filepath: str, dataset_dir: str
):
    """Create QA pairs from a corpus using specified LLM and preset configuration.

    Args:
            qa_creation_request (QACreationRequest): Configuration object containing:
                    - preset: Type of QA generation ("basic", "simple", or "advanced")
                    - llm_config: LLM configuration (name and parameters)
                    - qa_num: Number of QA pairs to generate
                    - lang: Target language for QA pairs
                    - name: Output filename prefix
            corpus_filepath (str): Path to the input corpus parquet file
            dataset_dir (str): Directory where the generated QA pairs will be saved

    Raises:
            ValueError: If an unsupported preset is specified

    Returns:
            None: Saves the generated QA pairs to a parquet file in dataset_dir
    """
    corpus_df = pd.read_parquet(corpus_filepath, engine="pyarrow")
    llm = generator_models[qa_creation_request.llm_config.llm_name](
        **qa_creation_request.llm_config.llm_params
    )

    if qa_creation_request.preset == "basic":
        qa: QA = default_create(
            corpus_df,
            llm,
            qa_creation_request.qa_num,
            qa_creation_request.lang,
            batch_size=8,
        )
    elif qa_creation_request.preset == "simple":
        qa: QA = fast_create(
            corpus_df,
            llm,
            qa_creation_request.qa_num,
            qa_creation_request.lang,
            batch_size=8,
        )
    elif qa_creation_request.preset == "advanced":
        qa: QA = advanced_create(
            corpus_df,
            llm,
            qa_creation_request.qa_num,
            qa_creation_request.lang,
            batch_size=8,
        )
    else:
        raise ValueError(f"Input not supported Preset {qa_creation_request.preset}")

    print(f"Generated QA jax : {qa.data}")
    print(f"QA jax shape : {qa.data.shape}")
    print(f"QA jax length : {len(qa.data)}")
    # dataset_dir will be folder ${PROJECT_DIR}/qa/
    qa.to_parquet(
        os.path.join(dataset_dir, f"{qa_creation_request.name}.parquet"),
        corpus_filepath,
    ) 