import logging
import os
import shutil
from typing import Optional

import pandas as pd

from autorag.data.index.run import run_indexer
from autorag.data.utils.util import load_yaml, get_param_combinations

logger = logging.getLogger("AutoRAG")


class Indexer:
    def __init__(self, chunk_df: pd.DataFrame, project_dir: Optional[str] = None):
        self.chunk_result = chunk_df
        self.project_dir = project_dir if project_dir is not None else os.getcwd()

    @classmethod
    def from_parquet(
        cls, chunk_data_path: str, project_dir: Optional[str] = None
    ) -> "Indexer":
        """
        Create Indexer instance from parquet file containing chunked data.
        
        Args:
            chunk_data_path: Path to the parquet file with chunked data
            project_dir: Project directory for saving results
            
        Returns:
            Indexer instance
        """
        if not os.path.exists(chunk_data_path):
            raise ValueError(f"chunk_data_path {chunk_data_path} does not exist.")
        if not chunk_data_path.endswith("parquet"):
            raise ValueError(
                f"chunk_data_path {chunk_data_path} is not a parquet file."
            )
        chunk_result = pd.read_parquet(chunk_data_path, engine="pyarrow")
        return cls(chunk_result, project_dir)

    def start_indexing(self, yaml_path: str):
        """
        Start the indexing process using configuration from YAML file.
        
        Args:
            yaml_path: Path to the YAML configuration file
        """
        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir)

        # Copy YAML file to the project directory (only if different location)
        dest_path = os.path.join(self.project_dir, "index_config.yaml")
        if os.path.abspath(yaml_path) != os.path.abspath(dest_path):
            shutil.copy(yaml_path, dest_path)

        # Load YAML file
        modules = load_yaml(yaml_path)

        input_modules, input_params = get_param_combinations(modules)

        logger.info("Indexing Start...")
        run_indexer(
            modules=input_modules,
            module_params=input_params,
            chunk_result=self.chunk_result,
            project_dir=self.project_dir,
        )
        logger.info("Indexing Done!") 