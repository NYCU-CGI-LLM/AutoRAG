from fastapi import FastAPI, Request, Response, HTTPException
import yaml
import os
from pathlib import Path
from typing import Dict, Any

app = FastAPI(title="AutoRAG YAML Configuration API")

# Define the directory to save uploaded YAML files
CONFIG_DIR = Path(__file__).parent / "configs"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/set_yaml", status_code=201)
async def set_yaml_config(request: Request) -> Dict[str, str]:
    """
    Receives YAML data in the request body and saves it to a file.
    The YAML content should be sent as raw text in the request body.
    """
    try:
        # Read the raw body from the request
        yaml_content_bytes = await request.body()
        yaml_content_str = yaml_content_bytes.decode('utf-8')

        # Validate YAML content (optional, but good practice)
        try:
            yaml_data = yaml.safe_load(yaml_content_str)
            if not isinstance(yaml_data, dict): # Or whatever root type you expect
                raise HTTPException(status_code=400, detail="Invalid YAML structure. Root must be a dictionary.")
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML format: {e}")

        # Define the file path
        file_path = CONFIG_DIR / "uploaded_config.yaml"

        # Save the YAML content to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content_str)
            
        return {"message": "YAML configuration saved successfully.", "file_path": str(file_path)}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
