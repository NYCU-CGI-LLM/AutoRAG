from datetime import datetime
from enum import Enum
from typing import Dict, Literal, Any, Optional

import numpy as np
from pydantic import BaseModel, Field, field_validator, ConfigDict
from .common import TaskStatusEnum, TaskType


class Project(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "id": "proj_123",
                "name": "My Project",
                "description": "A sample project",
                "created_at": "2024-02-11T12:00:00Z",
                "status": "active",
                "metadata": {},
            },
            "deprecated": True
        },
    )

    id: str
    name: str
    description: str
    created_at: datetime
    status: Literal["active", "archived"]
    metadata: Dict[str, Any]

class TrialCreateRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"deprecated": True})
    name: Optional[str] = Field(None, description="The name of the trial")
    raw_path: Optional[str] = Field(None, description="The path to the raw data")
    corpus_path: Optional[str] = Field(None, description="The path to the corpus data")
    qa_path: Optional[str] = Field(None, description="The path to the QA data")
    config: Optional[Dict] = Field(
        None, description="The trial configuration dictionary"
    )


class TrialConfig(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, 
        validate_assignment=True,
        json_schema_extra={"deprecated": True}
    )

    trial_id: Optional[str] = Field(None, description="The trial id")
    project_id: str
    save_dir: Optional[str] = Field(
        None, description="The directory that trial result is stored."
    )
    corpus_name: Optional[str] = None
    qa_name: Optional[str] = None
    config: Optional[dict] = None
    metadata: Optional[dict] = {}


class Trial(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, 
        validate_assignment=True,
        json_schema_extra={"deprecated": True}
    )

    id: str
    project_id: str
    config: Optional[TrialConfig] = None
    name: str
    status: TaskStatusEnum
    created_at: datetime
    report_task_id: Optional[str] = Field(
        None, description="The report task id for forcing shutdown of the task"
    )
    chat_task_id: Optional[str] = Field(
        None, description="The chat task id for forcing shutdown of the task"
    )
    api_pid: Optional[int] = Field(None, description="The process id of the API server")

    @field_validator("report_task_id", "chat_task_id", mode="before")
    def replace_nan_with_none(cls, v):
        if isinstance(v, float) and np.isnan(v):
            return None
        return v

    # 경로 유효성 검사 메서드 추가
    def validate_paths(self) -> bool:
        """
        모든 필수 경로가 유효한지 검사
        """
        import os

        return all(
            [
                os.path.exists(self.corpus_path),
                os.path.exists(self.qa_path),
                os.path.exists(self.config_path),
            ]
        )

    # 경로 생성 메서드 추가
    def create_directories(self) -> None:
        """
        필요한 디렉토리 구조 생성
        """
        import os

        paths = [
            os.path.dirname(self.corpus_path),
            os.path.dirname(self.qa_path),
            os.path.dirname(self.config_path),
        ]
        for path in paths:
            os.makedirs(path, exist_ok=True)

class Task(BaseModel):
    model_config = ConfigDict(json_schema_extra={"deprecated": True})
    id: str = Field(description="The task id")
    project_id: str
    trial_id: str = Field(description="The trial id", default="")
    name: Optional[str] = Field(None, description="The name of the task")
    config_yaml: Optional[Dict] = Field(
        None,
        description="YAML configuration. Format is dictionary, not path of the YAML file.",
    )
    status: TaskStatusEnum
    error_message: Optional[str] = Field(
        None, description="Error message if the task failed"
    )
    type: TaskType
    created_at: Optional[datetime] = None
    save_path: Optional[str] = Field(
        None,
        description="Path where the task results are saved. It will be directory or file.",
    )


# Definitions for QACreation copied from AutoRAG/temp/api/src/schema.py
# These are assumed to be active and NOT deprecated.
class QACreationPresetEnum(str, Enum):
    BASIC = "basic"
    SIMPLE = "simple"
    ADVANCED = "advanced"


class LLMConfig(BaseModel):
    llm_name: str = Field(description="Name of the LLM model")
    llm_params: dict = Field(description="Parameters for the LLM model", default={})


class SupportLanguageEnum(str, Enum):
    ENGLISH = "en"
    KOREAN = "ko"
    JAPANESE = "ja"


class QACreationRequest(BaseModel):
    preset: QACreationPresetEnum
    name: str = Field(..., description="Name of the QA dataset")
    chunked_name: str = Field(..., description="The name of the chunked data")
    qa_num: int
    llm_config: LLMConfig = Field(description="LLM configuration settings")
    lang: SupportLanguageEnum = Field(
        default=SupportLanguageEnum.ENGLISH, description="Language of the QA dataset"
    )

# Potentially other deprecated schemas like ParseRequest, ChunkRequest, EnvVariableRequest
# from the source file are NOT copied over as they were not part of the immediate ImportError.
# If they are needed, they can be added separately.
