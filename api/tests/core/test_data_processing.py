import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
import pathlib
import pandas as pd

from app.core.data_processing import (
    run_parser_start_parsing, 
    run_chunker_start_chunking, 
    _DEFAULT_PARSER_YAML_PATH, 
    _DEFAULT_CHUNKER_YAML_PATH
)

# Expected hardcoded YAML path relative to data_processing.py
# data_processing.py is in app/core/
# config is in api/config -> ../../config from app/core
EXPECTED_HARDCODED_YAML_NAME = "file_types_full.yaml"

# For checking the name of the default YAML file for parser
DEFAULT_PARSER_YAML_FILENAME = os.path.basename(_DEFAULT_PARSER_YAML_PATH)

# For checking the name of the default YAML file for chunker
DEFAULT_CHUNKER_YAML_FILENAME = os.path.basename(_DEFAULT_CHUNKER_YAML_PATH)

class TestDataProcessing(unittest.TestCase):

    @patch('app.core.data_processing.logger')
    @patch('app.core.data_processing.Parser')
    def test_run_parser_start_parsing_with_custom_yaml(self, MockParser, mock_logger):
        """Test run_parser_start_parsing when a custom YAML path is provided."""
        mock_parser_instance = MagicMock()
        MockParser.return_value = mock_parser_instance

        test_data_path_glob = "*.txt"
        test_save_dir = "/test/project_custom_save"
        custom_yaml_path = "/custom/path/to/my_config.yaml"
        test_all_files = True

        run_parser_start_parsing(test_data_path_glob, test_save_dir, test_all_files, yaml_path=custom_yaml_path)

        MockParser.assert_called_once_with(data_path_glob=test_data_path_glob, project_dir=test_save_dir)
        mock_parser_instance.start_parsing.assert_called_once_with(custom_yaml_path, all_files=test_all_files)

        logged_info_str = " ".join(call_args[0][0] for call_args in mock_logger.info.call_args_list if isinstance(call_args[0][0], str))
        self.assertIn(f"Parser started with data_path_glob: {test_data_path_glob}", logged_info_str)
        self.assertIn(f"save_dir: {test_save_dir}", logged_info_str)
        self.assertIn(f"using yaml_path: {custom_yaml_path}", logged_info_str)
        mock_logger.info.assert_any_call("Parser completed")

    @patch('app.core.data_processing.logger')
    @patch('app.core.data_processing.Parser')
    def test_run_parser_start_parsing_with_default_yaml(self, MockParser, mock_logger):
        """Test run_parser_start_parsing when YAML path is omitted (uses default)."""
        mock_parser_instance = MagicMock()
        MockParser.return_value = mock_parser_instance

        test_data_path_glob = "*.csv"
        test_save_dir = "/test/project_default_save"
        test_all_files = False

        run_parser_start_parsing(test_data_path_glob, test_save_dir, test_all_files)

        MockParser.assert_called_once_with(data_path_glob=test_data_path_glob, project_dir=test_save_dir)
        
        called_yaml_path = mock_parser_instance.start_parsing.call_args[0][0]
        self.assertEqual(called_yaml_path, _DEFAULT_PARSER_YAML_PATH)
        mock_parser_instance.start_parsing.assert_called_once_with(_DEFAULT_PARSER_YAML_PATH, all_files=test_all_files)

        logged_info_str = " ".join(call_args[0][0] for call_args in mock_logger.info.call_args_list if isinstance(call_args[0][0], str))
        self.assertIn(f"Parser started with data_path_glob: {test_data_path_glob}", logged_info_str)
        self.assertIn(f"save_dir: {test_save_dir}", logged_info_str)
        self.assertIn(f"using yaml_path: {_DEFAULT_PARSER_YAML_PATH}", logged_info_str)
        mock_logger.info.assert_any_call("Parser completed")

    @patch('app.core.data_processing.logger')
    @patch('app.core.data_processing.Chunker')
    def test_run_chunker_start_chunking_with_custom_yaml(self, MockChunker, mock_logger):
        """Test run_chunker_start_chunking when a custom YAML path is provided."""
        mock_chunker_instance = MagicMock()
        MockChunker.from_parquet.return_value = mock_chunker_instance

        test_raw_path = "/test/raw_data.parquet"
        test_save_dir = "/test/project_chunk_custom_save"
        custom_chunker_yaml_path = "/custom/chunker_config.yaml"

        run_chunker_start_chunking(test_raw_path, test_save_dir, yaml_path=custom_chunker_yaml_path)

        MockChunker.from_parquet.assert_called_once_with(test_raw_path, project_dir=test_save_dir)
        mock_chunker_instance.start_chunking.assert_called_once_with(custom_chunker_yaml_path)

        mock_logger.info.assert_any_call(f"Chunker initialized for raw_path: {test_raw_path}, save_dir: {test_save_dir}")
        mock_logger.info.assert_any_call(f"Chunking completed using yaml_path: {custom_chunker_yaml_path} within save_dir: {test_save_dir}")

    @patch('app.core.data_processing.logger')
    @patch('app.core.data_processing.Chunker')
    def test_run_chunker_start_chunking_with_default_yaml(self, MockChunker, mock_logger):
        """Test run_chunker_start_chunking when YAML path is omitted (uses default)."""
        mock_chunker_instance = MagicMock()
        MockChunker.from_parquet.return_value = mock_chunker_instance

        test_raw_path = "/test/raw_data_default.parquet"
        test_save_dir = "/test/project_chunk_default_save"

        run_chunker_start_chunking(test_raw_path, test_save_dir)

        MockChunker.from_parquet.assert_called_once_with(test_raw_path, project_dir=test_save_dir)
        mock_chunker_instance.start_chunking.assert_called_once_with(_DEFAULT_CHUNKER_YAML_PATH)
        
        mock_logger.info.assert_any_call(f"Chunker initialized for raw_path: {test_raw_path}, save_dir: {test_save_dir}")
        mock_logger.info.assert_any_call(f"Chunking completed using yaml_path: {_DEFAULT_CHUNKER_YAML_PATH} within save_dir: {test_save_dir}")

    @patch('app.core.data_processing.logger') # Still mock logger
    def test_run_parser_start_parsing_integration(self, mock_logger):
        """Integration test for run_parser_start_parsing, using the default YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = pathlib.Path(tmpdir)
            input_files_dir = save_dir / "source_data_for_integration"
            input_files_dir.mkdir()

            # We will now rely on the default YAML (file_types_full.yaml)
            # Ensure that file_types_full.yaml is appropriate for parsing .txt files for this test.

            sample_text_file = input_files_dir / "sample1.txt"
            sample_text_content = "This is the first sample document for integration.\nIt has two lines."
            with open(sample_text_file, "w") as f:
                f.write(sample_text_content)
            
            sample_text_file_2 = input_files_dir / "sample2.txt"
            sample_text_content_2 = "This is a second document for integration."
            with open(sample_text_file_2, "w") as f:
                f.write(sample_text_content_2)

            data_path_glob = str(input_files_dir / "*.txt")
            all_files = True

            # Call without yaml_path to test default behavior
            run_parser_start_parsing(
                data_path_glob=data_path_glob,
                save_dir=str(save_dir),
                all_files=all_files
            )

            logged_info_str = " ".join(call_args[0][0] for call_args in mock_logger.info.call_args_list if isinstance(call_args[0][0], str))
            self.assertIn(f"Parser started with data_path_glob: {data_path_glob}", logged_info_str)
            self.assertIn(f"save_dir: {str(save_dir)}", logged_info_str)
            self.assertIn(f"using yaml_path: {_DEFAULT_PARSER_YAML_PATH}", logged_info_str)
            mock_logger.info.assert_any_call("Parser completed")

            expected_output_path = save_dir / "data" / "parsed_data.parquet"
            self.assertTrue(expected_output_path.exists(), f"Output parquet file not found at {expected_output_path}")
            self.assertTrue(expected_output_path.is_file(), f"{expected_output_path} is not a file.")

            if expected_output_path.exists() and expected_output_path.is_file():
                df = pd.read_parquet(expected_output_path)
                self.assertFalse(df.empty, "Parsed data parquet file is empty.")
                # The content check might need adjustment if file_types_full.yaml processes .txt differently
                # For now, we'll keep the existing checks.
                self.assertEqual(len(df), 2, "Parsed DataFrame should contain 2 rows for 2 documents.") 
                self.assertIn("text", df.columns, "Column 'text' not found in parsed data.")
                self.assertIn("id", df.columns, "Column 'id' not found in parsed data.")
                
                expected_text_1 = sample_text_content.replace("\\n", "\n")
                self.assertTrue(any(expected_text_1 in t for t in df["text"].tolist()), f"Content of sample1.txt not found in parsed data. Parsed texts: {df['text'].tolist()}")
                self.assertTrue(any(sample_text_content_2 in t for t in df["text"].tolist()), f"Content of sample2.txt not found in parsed data. Parsed texts: {df['text'].tolist()}")

if __name__ == '__main__':
    unittest.main() 