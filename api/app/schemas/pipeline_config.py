from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ModuleModel(BaseModel):
    module_type: str
    class Config:
        extra = "allow"

class NodeModel(BaseModel):
    node_type: str
    strategy: Dict[str, Any] = Field(default_factory=dict)
    modules: List[ModuleModel]

class NodeLineModel(BaseModel):
    node_line_name: str
    nodes: List[NodeModel]

class VectordbConfigModel(BaseModel):
    name: str
    db_type: str
    client_type: str
    embedding_model: str
    collection_name: str
    path: str

class PipelineConfigModel(BaseModel):
    node_lines: List[NodeLineModel]
    vectordb: Optional[List[VectordbConfigModel]] = None 