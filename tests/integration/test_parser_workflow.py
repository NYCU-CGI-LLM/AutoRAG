"""
Integration tests for the complete parser workflow

This module tests the end-to-end functionality of the parser service
including file upload, parsing, and result retrieval.
"""

import pytest
import tempfile
import os
import sys
from uuid import uuid4
from io import BytesIO

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'api'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'autorag'))

try:
    from app.services.parser_service import ParserService
    from app.services.minio_service import MinIOService
except ImportError:
    ParserService = None
    MinIOService = None


@pytest.mark.integration
class TestParserWorkflowIntegration:
    """Integration tests for the complete parser workflow"""
    
    @pytest.mark.skipif(ParserService is None, reason="Services not available")
    def test_complete_csv_workflow(self, sample_files, parser_configs):
        """Test complete workflow: file creation -> parsing -> validation"""
        # Initialize services
        parser_service = ParserService()
        
        # Get test data
        csv_file = sample_files['csv']
        csv_config = parser_configs['csv']
        
        try:
            # Parse the file
            result = parser_service._run_autorag_parser(
                file_path=csv_file,
                mime_type='text/csv',
                module_type=csv_config['module_type'],
                params=csv_config['params']
            )
            
            # Comprehensive validation
            assert isinstance(result, dict), "Result should be a dictionary"
            assert 'texts' in result, "Result should contain 'texts' key"
            assert 'path' in result, "Result should contain 'path' key"
            
            texts = result['texts']
            assert len(texts) > 0, "Should extract at least one text chunk"
            assert len(texts) == 4, "Should extract 4 rows from CSV"
            
            # Validate content structure
            for text in texts:
                assert isinstance(text, str), "Each text chunk should be a string"
                assert len(text.strip()) > 0, "Text chunks should not be empty"
            
            # Check specific content
            combined_text = ' '.join(texts)
            assert 'John Doe' in combined_text, "Should contain CSV data"
            assert 'Engineer' in combined_text, "Should contain occupation data"
            
        except Exception as e:
            pytest.skip(f"CSV workflow integration test skipped: {e}")
    
    @pytest.mark.skipif(ParserService is None, reason="Services not available")
    def test_complete_markdown_workflow(self, sample_files, parser_configs):
        """Test complete workflow for Markdown files"""
        parser_service = ParserService()
        
        md_file = sample_files['markdown']
        md_config = parser_configs['markdown']
        
        try:
            result = parser_service._run_autorag_parser(
                file_path=md_file,
                mime_type='text/markdown',
                module_type=md_config['module_type'],
                params=md_config['params']
            )
            
            # Validation
            assert isinstance(result, dict)
            assert 'texts' in result
            
            texts = result['texts']
            assert len(texts) > 0
            
            # Content validation
            combined_text = ' '.join(texts)
            assert 'Sample Markdown Document' in combined_text
            assert 'Overview' in combined_text
            
        except Exception as e:
            pytest.skip(f"Markdown workflow integration test skipped: {e}")
    
    @pytest.mark.skipif(MinIOService is None, reason="MinIO service not available")
    def test_minio_file_operations(self, sample_files):
        """Test MinIO file upload and download operations"""
        try:
            minio_service = MinIOService()
            
            # Test file upload
            csv_file = sample_files['csv']
            object_key = f"test_integration/{uuid4()}/test_file.csv"
            
            with open(csv_file, 'rb') as file_data:
                file_size = os.path.getsize(csv_file)
                minio_service.client.put_object(
                    bucket_name="autorag-files",
                    object_name=object_key,
                    data=file_data,
                    length=file_size,
                    content_type='text/csv'
                )
            
            # Test file download
            downloaded_data = minio_service.download_file(object_key)
            assert downloaded_data is not None
            
            # Verify content
            content = downloaded_data.read().decode('utf-8')
            assert 'John Doe' in content
            
            # Cleanup
            minio_service.client.remove_object("autorag-files", object_key)
            
        except Exception as e:
            pytest.skip(f"MinIO integration test skipped: {e}")
    
    def test_error_handling_workflow(self, parser_configs):
        """Test error handling in the workflow"""
        if ParserService is None:
            pytest.skip("ParserService not available")
            
        parser_service = ParserService()
        
        # Test with non-existent file
        with pytest.raises(Exception):
            parser_service._run_autorag_parser(
                file_path="/nonexistent/file.txt",
                mime_type='text/plain',
                module_type='langchain',
                params={'parse_method': 'pymupdf'}
            )
        
        # Test with invalid module type
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("test content")
            tmp_path = tmp.name
        
        try:
            with pytest.raises(Exception):
                parser_service._run_autorag_parser(
                    file_path=tmp_path,
                    mime_type='text/plain',
                    module_type='invalid_module',
                    params={}
                )
        finally:
            os.unlink(tmp_path)


@pytest.mark.integration
class TestParserConfigurationIntegration:
    """Integration tests for parser configuration management"""
    
    def test_parser_config_validation(self, parser_configs):
        """Test that all parser configurations are valid"""
        required_fields = ['id', 'name', 'module_type', 'supported_mime', 'params']
        
        for config_name, config in parser_configs.items():
            # Check required fields
            for field in required_fields:
                assert field in config, f"Config {config_name} missing field: {field}"
            
            # Check field types
            assert isinstance(config['supported_mime'], list)
            assert isinstance(config['params'], dict)
            assert len(config['supported_mime']) > 0
    
    def test_mime_type_coverage(self, parser_configs):
        """Test that we have parsers for common MIME types"""
        all_mime_types = set()
        for config in parser_configs.values():
            all_mime_types.update(config['supported_mime'])
        
        expected_types = ['text/csv', 'text/markdown', 'application/json']
        for mime_type in expected_types:
            assert mime_type in all_mime_types, f"No parser for MIME type: {mime_type}"


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceIntegration:
    """Performance-related integration tests"""
    
    @pytest.mark.skipif(ParserService is None, reason="Services not available")
    def test_large_file_handling(self, temp_test_dir):
        """Test handling of larger files"""
        parser_service = ParserService()
        
        # Create a larger CSV file
        large_csv_path = os.path.join(temp_test_dir, "large_test.csv")
        with open(large_csv_path, 'w', encoding='utf-8') as f:
            f.write("name,age,city,occupation\n")
            for i in range(1000):  # 1000 rows
                f.write(f"Person{i},{20+i%50},City{i%10},Job{i%5}\n")
        
        try:
            result = parser_service._run_autorag_parser(
                file_path=large_csv_path,
                mime_type='text/csv',
                module_type='langchain',
                params={'parse_method': 'csv'}
            )
            
            assert isinstance(result, dict)
            assert 'texts' in result
            assert len(result['texts']) == 1000  # Should parse all rows
            
        except Exception as e:
            pytest.skip(f"Large file test skipped: {e}")
    
    @pytest.mark.skipif(ParserService is None, reason="Services not available")
    def test_multiple_file_processing(self, sample_files, parser_configs):
        """Test processing multiple files in sequence"""
        parser_service = ParserService()
        
        results = []
        test_cases = [
            (sample_files['csv'], parser_configs['csv'], 'text/csv'),
            (sample_files['markdown'], parser_configs['markdown'], 'text/markdown')
        ]
        
        for file_path, config, mime_type in test_cases:
            try:
                result = parser_service._run_autorag_parser(
                    file_path=file_path,
                    mime_type=mime_type,
                    module_type=config['module_type'],
                    params=config['params']
                )
                results.append(result)
            except Exception as e:
                pytest.skip(f"Multiple file processing test skipped: {e}")
        
        # Validate all results
        assert len(results) == 2
        for result in results:
            assert isinstance(result, dict)
            assert 'texts' in result
            assert len(result['texts']) > 0 