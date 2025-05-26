# Database Setup Guide

This project uses PostgreSQL with SQLModel (built on SQLAlchemy) and Alembic for database migrations.

## Architecture

- **Database**: PostgreSQL 15
- **ORM**: SQLModel (FastAPI's recommended ORM, built on SQLAlchemy)
- **Migrations**: Alembic
- **Database Management**: Adminer (web-based database management tool)

## Database Schema

The database follows the schema shown in the project diagram with the following tables:

- `user` - User accounts
- `library` - Document libraries (regular/bench types)
- `file` - Files within libraries
- `retriever` - Retriever configurations
- `vectordb_retriever` - Vector database retriever settings
- `bm25_retriever` - BM25 retriever settings
- `chat` - Chat sessions
- `dialog` - Individual messages in chats

## Quick Start

### 1. Start the Database

```bash
docker-compose up postgres adminer -d
```

### 2. Run Migrations

The entrypoint script automatically runs migrations, but you can also run them manually:

```bash
cd api
python run_migrations.py
```

Or using Alembic directly:

```bash
cd api
alembic upgrade head
```

### 3. Access Database Management

- **Adminer**: http://localhost:8080
  - Server: `postgres`
  - Username: `autorag_user`
  - Password: `autorag_password`
  - Database: `autorag_db`

## Development Workflow

### Creating New Migrations

1. Modify your SQLModel models in `api/app/models/`
2. Generate a new migration:
   ```bash
   cd api
   alembic revision --autogenerate -m "Description of changes"
   ```
3. Review the generated migration file in `api/alembic/versions/`
4. Apply the migration:
   ```bash
   alembic upgrade head
   ```

### Database Models

All models are defined using SQLModel in `api/app/models/`:

- `user.py` - User model
- `library.py` - Library model
- `file.py` - File model
- `retriever.py` - Retriever, VectorDBRetriever, BM25Retriever models
- `chat.py` - Chat model
- `dialog.py` - Dialog model

### Using Database in FastAPI

```python
from fastapi import Depends
from sqlmodel import Session
from app.core.database import get_session

@app.get("/users/")
def read_users(session: Session = Depends(get_session)):
    users = session.exec(select(User)).all()
    return users
```

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
  - Default: `postgresql://autorag_user:autorag_password@localhost:5432/autorag_db`
  - Docker: `postgresql://autorag_user:autorag_password@postgres:5432/autorag_db`

## Troubleshooting

### Migration Issues

1. **Foreign key errors**: Ensure your models have proper foreign key relationships
2. **Import errors**: Make sure all models are imported in `alembic/env.py`
3. **Connection errors**: Verify PostgreSQL is running and accessible

### Reset Database

To completely reset the database:

```bash
# Stop services
docker-compose down

# Remove database volume
docker volume rm autorag_cgi_postgres_data

# Restart services
docker-compose up postgres adminer -d

# Run migrations
cd api && python run_migrations.py
```

## Database Connection Details

- **Host**: localhost (or `postgres` from within Docker)
- **Port**: 5432
- **Database**: autorag_db
- **Username**: autorag_user
- **Password**: autorag_password 