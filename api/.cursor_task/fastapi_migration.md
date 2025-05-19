# FastAPI HTTP API Migration Plan

This document outlines the sub-tasks for migrating the existing HTTP API to FastAPI, following the structure defined in `.cursor_task/structure.md`.

## 1. Scaffold Project Structure
- [x] Create `app/` directory with:
  - [x] `__init__.py`
  - [x] `main.py` (FastAPI instance and application entry)
  - [x] `core/` subdirectory for configuration and security modules
  - [x] `schemas/` subdirectory for Pydantic models
  - [x] `routes/` subdirectory for API routers

## 2. Configuration and Environment
- [x] Implement `core/config.py` using Pydantic `BaseSettings` to load environment variables
- [ ] Remove existing environment loading logic from `app.py`
- [x] Use `.env.dev` or `.env` for configuration

## 3. Security and Authentication
- [x] Create `core/security.py` with JWT token creation and validation (using `python-jose`)
- [x] Define security dependencies (`get_current_user`) for protected endpoints
- [x] Add CORS and other middleware in `main.py`

## 4. API Routes and Schemas
- [ ] Identify all existing endpoints in `app.py`
- [ ] Define request/response Pydantic schemas for each endpoint in `schemas/`
- [ ] Create router modules under `routes/` for each logical group of endpoints:
  - `auth.py`: authentication (login, token, protected routes)
  - `projects.py`: `/projects` CRUD operations
  - `trials.py`: `/projects/{project_id}/trials` endpoints
  - `uploads.py`: `/projects/{project_id}/upload` file uploads
  - `parse.py`: `/projects/{project_id}/parse` operations
  - `chunk.py`: `/projects/{project_id}/chunk` operations
  - `qa.py`: `/projects/{project_id}/qa` operations
  - `tasks.py`: `/projects/{project_id}/tasks` status checks
  - `report.py`: `/projects/{project_id}/trials/{trial_id}/report` open/close
  - `chat.py`: `/projects/{project_id}/trials/{trial_id}/chat` open/close
  - `api_server.py`: `/projects/{project_id}/trials/{trial_id}/api` open/close
  - `env.py`: `/env` CRUD of environment variables
  - `artifacts.py`: `/projects/{project_id}/artifacts` and `/artifacts/content`
  - `routes_list.py`: listing all routes `/routes`
- [ ] In each router module:
  - [ ] Instantiate `APIRouter(prefix=..., tags=[...])`
  - [ ] Move corresponding endpoint implementations from `app.py` into router
- [ ] In `main.py`:
  - [ ] Import each router module
  - [ ] Include routers using `app.include_router(router)` with correct prefixes and tags

## 5. Database Integration
- [ ] Create `core/db.py` for database session management (SQLAlchemy or other)
- [ ] Refactor existing database utilities in `database/` to use new session
- [ ] Inject DB session into endpoints via dependencies

## 6. Celery Integration
- [ ] Configure Celery app in `core/celery.py` or integrate with existing `celery_app.py`
- [ ] Ensure FastAPI can invoke background tasks
- [ ] Optionally expose HTTP endpoints to trigger tasks

## 7. Docker and Deployment
- [ ] Update `Dockerfile` to install and run Uvicorn
- [ ] Modify `entrypoint.sh` to launch `uvicorn app.main:app`
- [ ] Test container startup and health checks

## 8. Documentation and Testing
- [ ] Verify OpenAPI schema and Swagger UI are generated
- [ ] Update `README.md` with instructions for FastAPI usage
- [ ] Refactor existing tests in `tests/` to use `pytest` and `httpx` for API testing