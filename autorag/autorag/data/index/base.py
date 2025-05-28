import functools
import logging
from typing import Tuple, List, Dict, Any

import pandas as pd

from autorag.utils import result_to_dataframe

logger = logging.getLogger("AutoRAG")


def indexer_node(func):
    @functools.wraps(func)
    @result_to_dataframe(["doc_id", "index_id", "index_type", "metadata"])
    def wrapper(
        chunk_result: pd.DataFrame, index_type: str, **kwargs
    ) -> Tuple[List[str], List[str], List[str], List[Dict[str, Any]]]:
        logger.info(f"Running indexer - {func.__name__} module...")

        # Get document IDs and contents from chunk result
        doc_ids = chunk_result["doc_id"].tolist()
        contents = chunk_result["contents"].tolist()
        
        # Get metadata from chunk result
        metadata_list = []
        for _, row in chunk_result.iterrows():
            metadata = {}
            # Copy relevant metadata fields
            for col in ["path", "start_end_idx", "metadata"]:
                if col in chunk_result.columns:
                    metadata[col] = row[col]
            metadata_list.append(metadata)

        # Run index module
        if func.__name__ == "vectordb_index":
            result = func(
                doc_ids=doc_ids,
                contents=contents,
                index_type=index_type,
                metadata_list=metadata_list,
                **kwargs
            )
            return result
        else:
            raise ValueError(f"Unsupported module_type: {func.__name__}")

    return wrapper 