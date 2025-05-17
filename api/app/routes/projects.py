from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from app.schemas.projects import Project, ProjectCreate
from app.core.config import settings
from database.project_db import SQLiteProjectDB

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate):
    work_dir = Path(settings.work_dir)
    new_project_dir = work_dir / project.name
    if new_project_dir.exists():
        raise HTTPException(status_code=400, detail=f"Project {project.name} already exists")
    # create project directories
    for sub in ["parse", "chunk", "qa", "project", "config", "raw_data"]:
        (new_project_dir / sub).mkdir(parents=True, exist_ok=True)
    # initialize project database
    SQLiteProjectDB(project.name)
    # save description
    desc_file = new_project_dir / "description.txt"
    desc_file.write_text(project.description or "")
    created_at = datetime.now(timezone.utc)
    return Project(
        id=project.name,
        name=project.name,
        description=project.description,
        created_at=created_at,
        status="active",
        metadata={},
    )

@router.get("", response_model=List[Project])
def list_projects():
    work_dir = Path(settings.work_dir)
    projects: List[Project] = []
    for item in work_dir.iterdir():
        if item.is_dir():
            proj_name = item.name
            desc_file = item / "description.txt"
            description = desc_file.read_text() if desc_file.exists() else ""
            created_at = datetime.fromtimestamp(item.stat().st_ctime, tz=timezone.utc)
            projects.append(
                Project(
                    id=proj_name,
                    name=proj_name,
                    description=description,
                    created_at=created_at,
                    status="active",
                    metadata={},
                )
            )
    return projects 