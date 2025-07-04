"""
Integration tests for Parser functionality
"""
import pytest
from fastapi.testclient import TestClient
import tempfile
import os


@pytest.mark.integration
class TestParserIntegration:
    """Integration tests for parser functionality"""
    
    def test_create_parser_endpoint(self, client: TestClient):
        """Test creating a parser via API endpoint"""
        parser_data = {
            "name": "test_langchain_parser",
            "module_type": "langchain",
            "supported_mime": ["application/pdf"],
            "params": {
                "parse_method": "pymupdf"
            }
        }
        
        response = client.post("/api/v1/parsers", json=parser_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == parser_data["name"]
        assert data["module_type"] == parser_data["module_type"]
        assert data["status"] == "ACTIVE"
    
    def test_get_parsers_endpoint(self, client: TestClient):
        """Test getting parsers via API endpoint"""
        # First create a parser
        parser_data = {
            "name": "test_parser_for_get",
            "module_type": "langchain",
            "supported_mime": ["application/pdf"],
            "params": {}
        }
        
        create_response = client.post("/api/v1/parsers", json=parser_data)
        assert create_response.status_code == 201
        
        # Then get all parsers
        response = client.get("/api/v1/parsers")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Check if our created parser is in the list
        parser_names = [p["name"] for p in data]
        assert "test_parser_for_get" in parser_names
    
    def test_get_parser_by_id_endpoint(self, client: TestClient):
        """Test getting a specific parser by ID"""
        # First create a parser
        parser_data = {
            "name": "test_parser_by_id",
            "module_type": "clova_ocr",
            "supported_mime": ["application/pdf"],
            "params": {
                "url": "test_url",
                "api_key": "test_key"
            }
        }
        
        create_response = client.post("/api/v1/parsers", json=parser_data)
        assert create_response.status_code == 201
        
        parser_id = create_response.json()["id"]
        
        # Then get the parser by ID
        response = client.get(f"/api/v1/parsers/{parser_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == parser_id
        assert data["name"] == parser_data["name"]
    
    def test_get_nonexistent_parser(self, client: TestClient):
        """Test getting a parser that doesn't exist"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/parsers/{fake_uuid}")
        
        assert response.status_code == 404
    
    @pytest.mark.slow
    def test_parse_file_workflow(self, client: TestClient, sample_pdf_file):
        """Test the complete file parsing workflow"""
        # Step 1: Create a parser
        parser_data = {
            "name": "integration_test_parser",
            "module_type": "langchain",
            "supported_mime": ["application/pdf"],
            "params": {
                "parse_method": "pymupdf"
            }
        }
        
        parser_response = client.post("/api/v1/parsers", json=parser_data)
        assert parser_response.status_code == 201
        parser_id = parser_response.json()["id"]
        
        # Step 2: Upload a file (assuming you have a file upload endpoint)
        with open(sample_pdf_file, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            upload_response = client.post("/api/v1/files/upload", files=files)
        
        # Note: This assumes you have a file upload endpoint
        # You might need to adjust this based on your actual API structure
        if upload_response.status_code == 201:
            file_id = upload_response.json()["id"]
            
            # Step 3: Parse the file
            parse_data = {
                "file_ids": [file_id],
                "parser_id": parser_id
            }
            
            parse_response = client.post("/api/v1/parse", json=parse_data)
            
            # The response might be async, so we might get a 202 (Accepted)
            assert parse_response.status_code in [200, 202]
            
            if parse_response.status_code == 200:
                results = parse_response.json()
                assert isinstance(results, list)
                assert len(results) == 1
                assert results[0]["file_id"] == file_id
    
    def test_invalid_parser_creation(self, client: TestClient):
        """Test creating a parser with invalid data"""
        invalid_data = {
            "name": "",  # Empty name should be invalid
            "module_type": "invalid_type",
            "supported_mime": [],
            "params": {}
        }
        
        response = client.post("/api/v1/parsers", json=invalid_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_parser_with_missing_fields(self, client: TestClient):
        """Test creating a parser with missing required fields"""
        incomplete_data = {
            "name": "incomplete_parser"
            # Missing module_type, supported_mime, params
        }
        
        response = client.post("/api/v1/parsers", json=incomplete_data)
        
        assert response.status_code == 422  # Validation error 