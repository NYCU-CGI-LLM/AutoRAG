# Project Structure Analysis for @api (`autorag_cgi/api/`)

This document provides an overview of the current project structure within the `autorag_cgi/api/` directory.

## Top-Level Directory Structure

The `autorag_cgi/api/` directory contains the following main components:

-   **`app/`**: The core application package containing all the FastAPI and Celery logic.
-   **`docs/`**: (This directory) Intended for project documentation.
-   **`tests/`**: Contains automated tests for the application.
-   **`data/`**: Likely used for storing data files, possibly related to projects or trials (contents not inspected).
-   **`.env.dev`**: Development environment configuration file (e.g., database URLs, Celery broker URLs, secrets).
-   **`.env.dev.example`**: An example template for the `.env.dev` file.
-   **`requirements.txt`**: Lists Python dependencies for the project.
-   **`Dockerfile`**: Configuration for building a Docker image of the application.
-   **`.dockerignore`**: Specifies files to exclude when building the Docker image.
-   **`.gitignore`**: Specifies intentionally untracked files that Git should ignore.
-   **`entrypoint.sh`**: A shell script often used as the entry point for the Docker container, possibly to start services or run migrations.
-   **`README.md`**: General information about the project.
-   **`_app.py`**: (Outside `app/`) This file's role is unclear from the name and location alone. It might be an older version of the main application or a utility script. Its high line count (1022 lines) suggests it contains significant logic. *Further investigation needed to determine its current relevance and whether its functionality should be integrated into `app/` or deprecated.*

## `app/` Directory Structure (Core Application)

The `app/` directory is the heart of the application and is structured as follows:

-   **`__init__.py`**: Marks `app/` as a Python package.
-   **`main.py`**: The main entry point for the FastAPI application. It initializes the FastAPI app, includes middleware, and mounts the various routers.
-   **`celery_app.py`**: Initializes the Celery application instance, loading configuration from `celeryconfig.py`. It also specifies which task modules Celery should discover (e.g., `app.tasks.trial_tasks`, `app.tasks.simple_tasks`).
-   **`celeryconfig.py`**: Contains the configuration settings for the Celery application. It loads settings from environment variables (defined in `.env.dev`).

### `app/core/`

This sub-package seems to hold core business logic, utility functions, and application-wide configurations.
-   **`__init__.py`**: Marks `app/core/` as a Python package.
-   **`config.py`**: Likely defines Pydantic models for application settings, loading values from environment variables (using `pydantic-settings`).
-   **`security.py`**: Probably contains security-related functions, such as password hashing, token generation/validation (e.g., for JWT).
-   **`db.py`**: Could be related to database session management or base ORM models (contents: 17 lines, suggests it might be simple or a utility).
-   **`run.py`**: Suggests functions or classes related to running specific processes, trials, or evaluations.
-   **`qa_create.py`**: Logic for QA (Question Answering) data creation.
-   **`validate.py`**: Functions for validation, possibly of configurations, data, or trial results.
-   **`evaluate_history.py`**: Logic for handling or processing evaluation history.

### `app/db/`

This sub-package is dedicated to database interaction.
-   **`project_db.py`**: Contains the `SQLiteProjectDB` class, responsible for managing interactions with an SQLite database, specifically for "trial" related data.

### `app/routers/` and `app/routes/`

These directories contain the FastAPI routers that define API endpoints. It appears there might be two conventions or a transition occurring, as both exist.
-   **`app/routers/__init__.py`** (Implicitly, if it's a package)
-   **`app/routers/simple_router.py`**: A router for utility tasks, like the simple string reversal Celery task example.
-   **`app/routes/__init__.py`**: Marks `app/routes/` as a Python package and may expose routers.
-   **`app/routes/projects.py`**: Endpoints related to managing "projects".
-   **`app/routes/knowledge_bases.py`**: Endpoints for managing "knowledge bases".
-   **`app/routes/variations.py`**: Endpoints for managing "variations" (likely nested under knowledge bases or projects).
-   **`app/routes/query.py`**: Endpoints for submitting queries, probably against knowledge bases/variations.
-   **`app/routes/tasks.py`**: Endpoints related to Celery tasks (possibly for checking status, though `simple_router.py` also has this).
-   **`app/routes/auth.py`**: Endpoints for authentication (e.g., login, register).

### `app/schemas/`

This sub-package holds Pydantic models used for data validation, serialization, and documentation of API request/response bodies.
-   **`__init__.py`**: Marks `app/schemas/` as a Python package and might expose common schemas.
-   **`_schema.py`**: A significant file (198 lines) likely containing many core Pydantic models, including `Trial` and `TrialConfig` used by `project_db.py`. The underscore prefix might indicate it's intended for internal use within the `schemas` package or is an older convention.
-   **`task_schemas.py`**: Schemas for Celery task requests and responses (e.g., `ReverseRequest`, `TaskResponse`).
-   **`projects.py`, `knowledge_base.py`, `variation.py`, `query.py`, `auth.py`**: Domain-specific Pydantic models corresponding to the routers in `app/routes/`.
-   **`common.py`**: Likely contains common or shared Pydantic models or fields used across different schemas.

### `app/tasks/`

This sub-package contains Celery task definitions.
-   **`__init__.py`** (Implicitly, if it's a package)
-   **`base.py`**: Defines base Celery task classes (e.g., `TrialTask`) that other tasks might inherit from, providing common functionality like state updating.
-   **`trial_tasks.py`**: Contains various Celery tasks related to "trials" (e.g., `chunk_documents`, `start_evaluate`).
-   **`simple_tasks.py`**: Contains the example `reverse_string_task`.
-   **`processing.py`**: An example task for document processing, currently with an unresolved `ProgressTask` dependency.

### `app/utils/`
This sub-package is intended for utility functions. The file `task_utils.py` (if moved here) would fit well.
- `__init__.py` (Implicitly, if it's a package)
- *(Currently empty or contents not listed)*

## `tests/` Directory Structure

Contains automated tests for the application.
-   **`test_app.py`**: Likely contains integration or functional tests for the FastAPI application and its endpoints.
-   **`test_project_db.py`**: Unit tests for the `SQLiteProjectDB` class and its database interactions.

## Architectural Overview

The project implements a web API using **FastAPI**.
-   It uses **Pydantic** for data validation and serialization (schemas).
-   It employs **Celery** for handling long-running background tasks, using **Redis** as the message broker and result backend.
-   Configuration is managed via environment variables, loaded from an `.env.dev` file using `python-dotenv` and `pydantic-settings` (in `app.core.config`).
-   Database interaction for "trials" is handled by a custom `SQLiteProjectDB` class, suggesting the use of **SQLite** for at least part of the data storage.
-   The project is set up for **Dockerization**, implying containerized deployment.
-   There's evidence of authentication (`app/core/security.py`, `app/routes/auth.py`).
-   The core domain appears to revolve around "projects," "knowledge bases," "variations," "trials," and "evaluations."

## Potential Areas for Review/Refinement

-   **`_app.py`**: The purpose and necessity of this top-level file should be clarified.
-   **`app/routers/` vs. `app/routes/`**: Standardize on one directory for routers to improve clarity.
-   **`app/schemas/_schema.py`**: The underscore prefix might be unconventional. Consider renaming or reorganizing its contents into more domain-specific files within `app/schemas/` for better discoverability, similar to how `task_schemas.py` and others are structured.
-   **`app/core/db.py`**: Clarify its role, especially with `app/db/project_db.py` existing.
-   **`src/` directory migration**: The original plan to migrate `src/` into `app/` needs to be completed, paying close attention to how `src/schema.py` integrates with the existing `app/schemas/` structure.
-   **Linter errors**: Address persistent linter errors related to imports, which might indicate issues with `PYTHONPATH` setup in the development environment or the linter's configuration. 