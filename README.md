# RAG System

A comprehensive RAG (Retrieval-Augmented Generation) system with web interface and API backend.

## About

This system was originally based on [AutoRAG](https://github.com/Marker-Inc-Korea/AutoRAG) but has been customized for specific use cases. For the original AutoRAG documentation and features, please visit the [AutoRAG GitHub repository](https://github.com/Marker-Inc-Korea/AutoRAG).

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git

### Installation

1. **Clone the UI repository**
   
   You need to clone the UI repository to use the web interface:
   ```bash
   git clone https://github.com/NYCU-CGI-LLM/rag-ui.git
   ```

2. **Configure API environment**
   
   Copy the environment example file and add your OpenAI API key:
   ```bash
   cp api/.env.dev.example api/.env.dev
   ```
   
   Edit `api/.env.dev` and add your OpenAI API key:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Start the system**
   
   Run the entire system using Docker Compose:
   ```bash
   docker compose up -d
   ```

### Services

Once the system is running, you can access the following services:

- **Web Interface**: http://localhost:3000
- **API Server**: http://localhost:8000
- **Database Admin (Adminer)**: http://localhost:8080
- **Flower (Celery Monitor)**: http://localhost:5555 (if enabled)

### System Architecture

The system includes the following components:

- **PostgreSQL**: Database for storing application data
- **Redis**: Cache and message broker
- **Qdrant**: Vector database for embeddings
- **MinIO**: Object storage for files
- **API Server**: FastAPI backend
- **Web UI**: Next.js frontend

### Environment Variables

The system uses the following key environment variables (configured in docker-compose.yml):

- `DATABASE_URL`: PostgreSQL connection string
- `MINIO_*`: MinIO storage configuration
- `REDIS_*`: Redis connection settings
- `QDRANT_*`: Qdrant vector database settings

### Usage

1. **Access the web interface** at http://localhost:3000
2. **Upload your documents** through the UI
3. **Configure your RAG pipeline** using the web interface
4. **Start querying** your documents

### API Documentation

Once the API server is running, you can access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Stopping the System

To stop all services:
```bash
docker compose down
```

To stop and remove all data:
```bash
docker compose down -v
```

### Troubleshooting

If you encounter issues:

1. **Check service logs**:
   ```bash
   docker compose logs [service_name]
   ```

2. **Restart services**:
   ```bash
   docker compose restart
   ```

3. **Rebuild containers**:
   ```bash
   docker compose up --build
   ```

## Original AutoRAG

For the original AutoRAG project with full documentation, tutorials, and community support, please visit:
- [AutoRAG GitHub Repository](https://github.com/Marker-Inc-Korea/AutoRAG)
- [AutoRAG Documentation](https://docs.auto-rag.com)

## Support

For issues related to this customized system, please create an issue in this repository.

For AutoRAG-related questions, please refer to the [AutoRAG repository](https://github.com/Marker-Inc-Korea/AutoRAG) and their [Discord community](https://discord.gg/P4DYXfmSAs).
