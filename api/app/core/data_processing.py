from autorag.parser import Parser
from autorag.chunker import Chunker


def run_parser_start_parsing(data_path_glob, project_dir, yaml_path, all_files: bool):
    # Import Parser here if it's defined in another module
    parser = Parser(data_path_glob=data_path_glob, project_dir=project_dir)
    print(
        f"Parser started with data_path_glob: {data_path_glob}, project_dir: {project_dir}, yaml_path: {yaml_path}"
    )
    parser.start_parsing(yaml_path, all_files=all_files)
    print("Parser completed")


def run_chunker_start_chunking(raw_path, project_dir, yaml_path):
    # Import Parser here if it's defined in another module
    chunker = Chunker.from_parquet(raw_path, project_dir=project_dir)
    chunker.start_chunking(yaml_path) 