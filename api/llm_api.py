from fastapi import FastAPI, Response
import sys
import os
from typing import Dict, List, Any

# Add project root to sys.path to import autorag module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autorag.nodes.generator import (
    LlamaIndexLLM,
    OpenAILLM,
    Vllm,
    VllmAPI,
    CoAGenerator
)
from autorag.nodes.generator.openai_llm import MAX_TOKEN_DICT

app = FastAPI(title="AutoRAG LLM API")

@app.get("/llm")
async def get_llm_info() -> Dict[str, Any]:
    """
    Get information about available generators and OpenAI LLM models
    """
    # List all available generators
    generators = {
        "LlamaIndexLLM": "LlamaIndex LLM integration",
        "OpenAILLM": "OpenAI API integration",
        "Vllm": "VLLM local deployment",
        "VllmAPI": "VLLM API integration",
        "CoAGenerator": "Chain of Abstraction generator"
    }
    
    # List all available OpenAI models
    openai_models = {k: v for k, v in MAX_TOKEN_DICT.items()}
    
    return {
        "available_generators": generators,
        "openai_llm_models": openai_models
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
