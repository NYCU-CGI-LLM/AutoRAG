import os
from typing import Callable, List, Dict
import pandas as pd

from autorag.strategy import measure_speed


def run_indexer(
    modules: List[Callable],
    module_params: List[Dict],
    chunk_result: pd.DataFrame,
    project_dir: str,
):
    """
    Run indexer modules on chunked data.
    
    Args:
        modules: List of indexer module functions
        module_params: List of parameter dictionaries for each module
        chunk_result: DataFrame containing chunked documents
        project_dir: Project directory to save results
    
    Returns:
        Summary DataFrame with execution results
    """
    results, execution_times = zip(
        *map(
            lambda x: measure_speed(x[0], chunk_result=chunk_result, **x[1]),
            zip(modules, module_params),
        )
    )
    average_times = list(map(lambda x: x / len(results[0]), execution_times))

    # Save results to parquet files
    filepaths = list(
        map(lambda x: os.path.join(project_dir, f"index_{x}.parquet"), range(len(modules)))
    )
    list(map(lambda x: x[0].to_parquet(x[1], index=False), zip(results, filepaths)))
    filenames = list(map(lambda x: os.path.basename(x), filepaths))

    summary_df = pd.DataFrame(
        {
            "filename": filenames,
            "module_name": list(map(lambda module: module.__name__, modules)),
            "module_params": module_params,
            "execution_time": average_times,
        }
    )
    summary_df.to_csv(os.path.join(project_dir, "index_summary.csv"), index=False)
    return summary_df 