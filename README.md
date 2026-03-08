# TerraChatBi

A production-ready full-stack AI agent application with FastAPI backend and Vue 3 frontend, featuring LangGraph integration for intelligent chatbot workflows.

## 🌟 Features

- **Production-Ready Architecture**

  - FastAPI backend with uvloop optimization for high-performance async API endpoints
  - Vue 3 + Vite frontend with Naive UI component library and TailwindCSS
  - LangGraph integration for AI agent workflows with state persistence
  - Langfuse for LLM observability and monitoring
  - Structured logging with structlog and environment-specific formatting
  - Rate limiting with configurable rules per endpoint
  - PostgreSQL with pgvector for data persistence and vector storage
  - Docker and Docker Compose support for easy deployment
  - Prometheus metrics and Grafana dashboards for monitoring

- **AI & LLM Features**

  - Long-term memory with mem0ai and pgvector for semantic memory storage
  - Multi-provider LLM support (OpenAI, Azure OpenAI, VLLM, custom endpoints)
  - LLM Service with automatic retry logic and backup model fallback
  - Dynamic AI model management with database configuration
  - Streaming responses for real-time chat interactions
  - Tool calling and function execution capabilities

- **Security**

  - JWT-based authentication with session management
  - Workspace-based multi-tenancy support
  - Role-based access control (RBAC)
  - Input sanitization and validation
  - CORS configuration
  - Rate limiting protection

- **Developer Experience**

  - Environment-specific configuration with automatic .env file loading
  - Comprehensive logging system with context binding
  - Clear project structure following best practices
  - Type hints throughout for better IDE support
  - Easy local development setup with Makefile commands
  - Automatic database migrations with Alembic

- **Model Evaluation Framework**
  - Automated metric-based evaluation of model outputs
  - Integration with Langfuse for trace analysis
  - Detailed JSON reports with success/failure metrics
  - Interactive command-line interface
  - Customizable evaluation metrics

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- Node.js 20.19.0+ or 22.12.0+
- PostgreSQL with pgvector extension
- Docker and Docker Compose (optional)

### Environment Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd TerraAgent
```

2. Setup backend:

```bash
cd backend
uv sync
cp .env.example .env.development
```

3. Setup frontend:

```bash
cd ../frontend
npm install
cp .env.example .env
```

4. Update the `.env` files with your configuration

### Database setup

1. Create a PostgreSQL database with pgvector extension
2. Update the database connection settings in your `.env` file:

```bash
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=terra-agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

Database tables are automatically created via Alembic migrations on application startup.

### Running the Application

#### Local Development

**Backend:**

```bash
# From project root
make backend-dev
# Or from backend directory
cd backend && uv run uvicorn app.main:app --reload --port 8000 --loop uvloop
```

**Frontend:**

```bash
# From project root
make frontend-dev
# Or from frontend directory
cd frontend && npm run dev
```

Access the application:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### Using Docker

```bash
# Build and run backend with Docker
make backend-docker-build-env ENV=development
make backend-docker-run-env ENV=development

# Build and run frontend with Docker
make frontend-docker-build
make frontend-docker-up
```

#### Monitoring Stack

```bash
# Start monitoring services (Prometheus + Grafana)
make backend-monitoring-up

# Access monitoring
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

The Docker setup includes:

- FastAPI application
- PostgreSQL database
- Prometheus for metrics collection
- Grafana for metrics visualization
- Pre-configured dashboards for API performance and system monitoring

## 📊 Model Evaluation

The project includes a robust evaluation framework for measuring and tracking model performance over time. The evaluator automatically fetches traces from Langfuse, applies evaluation metrics, and generates detailed reports.

### Running Evaluations

You can run evaluations with different options using the provided Makefile commands:

```bash
# Interactive mode with step-by-step prompts
make eval [ENV=development|staging|production]

# Quick mode with default settings (no prompts)
make eval-quick [ENV=development|staging|production]

# Evaluation without report generation
make eval-no-report [ENV=development|staging|production]
```

### Evaluation Features

- **Interactive CLI**: User-friendly interface with colored output and progress bars
- **Flexible Configuration**: Set default values or customize at runtime
- **Detailed Reports**: JSON reports with comprehensive metrics including:
  - Overall success rate
  - Metric-specific performance
  - Duration and timing information
  - Trace-level success/failure details

### Customizing Metrics

Evaluation metrics are defined in `evals/metrics/prompts/` as markdown files:

1. Create a new markdown file (e.g., `my_metric.md`) in the prompts directory
2. Define the evaluation criteria and scoring logic
3. The evaluator will automatically discover and apply your new metric

### Viewing Reports

Reports are automatically generated in the `evals/reports/` directory with timestamps in the filename:

```
evals/reports/evaluation_report_YYYYMMDD_HHMMSS.json
```

Each report includes:

- High-level statistics (total trace count, success rate, etc.)
- Per-metric performance metrics
- Detailed trace-level information for debugging

## 🔧 Configuration

The application uses a flexible configuration system with environment-specific settings:

- `.env.development` - Local development settings
- `.env.staging` - Staging environment settings
- `.env.production` - Production environment settings

### Environment Variables

```bash
# Application
PROJECT_NAME="TerraChatBi"
APP_ENV=development

# Database
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=terra-agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Langfuse (LLM Observability)
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com

# JWT Configuration
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_DAYS=30
DEFAULT_PWD="Terra@123456"

# Cache Settings
CACHE_TYPE=memory
# CACHE_REDIS_URL=redis://localhost:6379/0

# Rate Limiting
RATE_LIMIT_DEFAULT=["200 per day", "50 per hour"]
RATE_LIMIT_CHAT="30 per minute"
RATE_LIMIT_CHAT_STREAM="20 per minute"
```

## 🧠 Long-Term Memory

The application includes a sophisticated long-term memory system powered by mem0ai and pgvector:

### Features

- **Semantic Memory Storage**: Stores and retrieves memories based on semantic similarity
- **User-Specific Memories**: Each user has their own isolated memory space
- **Automatic Memory Management**: Memories are automatically extracted, stored, and retrieved
- **Vector Search**: Uses pgvector for efficient similarity search
- **Configurable Models**: Separate models for memory processing and embeddings

### How It Works

1. **Memory Addition**: During conversations, important information is automatically extracted and stored
2. **Memory Retrieval**: Relevant memories are retrieved based on conversation context
3. **Memory Search**: Semantic search finds related memories across conversations
4. **Memory Updates**: Existing memories can be updated as new information becomes available

## 🤖 LLM Service

The LLM service provides robust, production-ready language model interactions with automatic retry logic and multi-provider support.

### Features

- **Multi-Provider Support**: OpenAI, Azure OpenAI, VLLM, and custom OpenAI-compatible endpoints
- **Dynamic Model Configuration**: AI models configured via database with runtime switching
- **Automatic Retries**: Uses tenacity for exponential backoff retry logic
- **Backup Model Fallback**: Automatic fallback to backup models on primary failure
- **Streaming Support**: Real-time streaming responses for chat interactions

### Supported Providers

| Provider | Use Case | Configuration |
| -------- | -------- | ------------- |
| OpenAI | Production workloads | API key + base URL |
| Azure OpenAI | Enterprise deployments | Azure endpoint + deployment name |
| VLLM | Self-hosted models | Custom endpoint URL |
| Custom | OpenAI-compatible APIs | Any compatible endpoint |

### Model Management

AI models are managed through the admin API:

- `POST /api/v1/system/aimodel` - Register new AI model
- `GET /api/v1/system/aimodel` - List all models
- `PUT /api/v1/system/aimodel/default/{id}` - Set default model
- `PUT /api/v1/system/aimodel/backup/{id}` - Set backup model
- `POST /api/v1/system/aimodel/status` - Test model connectivity

### Retry Configuration

- Automatically retries on API timeouts, rate limits, and temporary errors
- **Max Attempts**: 2
- **Wait Strategy**: Exponential backoff (1s, 2s, 4s)
- **Logging**: All retry attempts are logged with context

## 📝 Advanced Logging

The application uses structlog for structured, contextual logging with automatic request tracking.

### Features

- **Structured Logging**: All logs are structured with consistent fields
- **Request Context**: Automatic binding of request_id, session_id, and user_id
- **Environment-Specific Formatting**: JSON in production, colored console in development
- **Performance Tracking**: Automatic logging of request duration and status
- **Exception Tracking**: Full stack traces with context preservation

### Logging Context Middleware

Every request automatically gets:
- Unique request ID
- Session ID (if authenticated)
- User ID (if authenticated)
- Request path and method
- Response status and duration

### Log Format Standards

- **Event Names**: lowercase_with_underscores
- **No F-Strings**: Pass variables as kwargs for proper filtering
- **Context Binding**: Always include relevant IDs and context
- **Appropriate Levels**: debug, info, warning, error, exception

## ⚡ Performance Optimizations

### uvloop Integration

The application uses uvloop for enhanced async performance (automatically enabled via Makefile):

**Performance Improvements**:
- 2-4x faster asyncio operations
- Lower latency for I/O-bound tasks
- Better connection pool management
- Reduced CPU usage for concurrent requests

### Connection Pooling

- **Database**: Async connection pooling with configurable pool size
- **LangGraph Checkpointing**: Shared connection pool for state persistence
- **Redis** (optional): Connection pool for caching

### Caching Strategy

- Only successful responses are cached
- Configurable TTL based on data volatility
- Cache invalidation on updates
- Supports Redis or in-memory caching

## 🔌 API Reference

### Authentication Endpoints

- `POST /api/v1/auth/login` - Authenticate and receive JWT token
- `POST /api/v1/auth/register` - Register a new user (admin only)
- `PATCH /api/v1/auth/users/me/password` - Change current user's password
- `PATCH /api/v1/auth/users/status` - Update user status (admin only)
- `DELETE /api/v1/auth/users/{user_id}` - Delete a user (admin only)

### User Management Endpoints

- `GET /api/v1/auth/users` - Get all users (admin only)
- `GET /api/v1/auth/users/by-email` - Get user by email (admin only)

### Workspace Management Endpoints

- `POST /api/v1/auth/workspaces` - Create a new workspace (admin only)
- `GET /api/v1/auth/workspaces` - Get all workspaces (admin only)
- `GET /api/v1/auth/workspaces/{workspace_id}` - Get workspace by ID
- `DELETE /api/v1/auth/workspaces/{workspace_id}` - Delete a workspace
- `POST /api/v1/auth/workspaces/{workspace_id}/users` - Add users to workspace
- `GET /api/v1/auth/workspaces/{workspace_id}/users` - Get workspace users
- `PATCH /api/v1/auth/users/switch/workspace` - Switch active workspace

### AI Model Management Endpoints

- `POST /api/v1/system/aimodel` - Create AI model (admin only)
- `GET /api/v1/system/aimodel` - List all AI models
- `GET /api/v1/system/aimodel/{id}` - Get AI model by ID
- `PUT /api/v1/system/aimodel` - Update AI model
- `DELETE /api/v1/system/aimodel/{id}` - Delete AI model
- `PUT /api/v1/system/aimodel/default/{id}` - Set default model
- `PUT /api/v1/system/aimodel/backup/{id}` - Set backup model
- `POST /api/v1/system/aimodel/status` - Test model connectivity

### Chat Endpoints

- `POST /api/v1/chatbot/chat` - Send message and receive response
- `POST /api/v1/chatbot/chat/stream` - Send message with streaming response
- `GET /api/v1/chatbot/messages` - Get conversation history
- `DELETE /api/v1/chatbot/messages` - Clear chat history

### Health & Monitoring

- `GET /` - Root endpoint with API info
- `GET /health` - Health check with database status
- `GET /metrics` - Prometheus metrics endpoint

For detailed API documentation, visit `/docs` (Swagger UI) or `/redoc` (ReDoc) when running the application.

## 📚 Project Structure

```
TerraAgent/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py              # Authentication & user management
│   │   │       ├── chatbot.py           # Chat endpoints
│   │   │       ├── api.py               # API router aggregation
│   │   │       └── system/
│   │   │           └── ai_model.py      # AI model management
│   │   ├── core/
│   │   │   ├── common/
│   │   │   │   ├── config.py            # Configuration management
│   │   │   │   ├── logging.py           # Structured logging
│   │   │   │   ├── metrics.py           # Prometheus metrics
│   │   │   │   ├── middleware/          # Custom middleware
│   │   │   │   ├── cache.py             # Caching layer
│   │   │   │   ├── db.py                # Database utilities
│   │   │   │   └── limiter.py           # Rate limiting
│   │   │   ├── langgraph/
│   │   │   │   ├── graph.py             # LangGraph agent
│   │   │   │   └── tools/               # Agent tools
│   │   │   ├── llm/
│   │   │   │   └── model_factory.py     # LLM factory & providers
│   │   │   └── prompts/                 # System prompts
│   │   ├── models/
│   │   │   ├── user.py                  # User & workspace models
│   │   │   ├── session.py               # Session model
│   │   │   └── ai_model.py              # AI model entity
│   │   ├── schemas/
│   │   │   ├── auth.py                  # Auth schemas
│   │   │   ├── chat.py                  # Chat schemas
│   │   │   └── graph.py                 # Graph state schemas
│   │   ├── services/
│   │   │   ├── auth.py                  # Auth service
│   │   │   ├── llm.py                   # LLM service with retries
│   │   │   ├── database.py              # Database service
│   │   │   └── system.py                # System service
│   │   ├── utils/
│   │   │   ├── auth.py                  # Auth utilities
│   │   │   ├── graph.py                 # Graph utilities
│   │   │   └── sanitization.py          # Input sanitization
│   │   └── main.py                      # Application entry point
│   ├── evals/
│   │   ├── evaluator.py                 # Evaluation logic
│   │   ├── main.py                      # Evaluation CLI
│   │   └── metrics/prompts/             # Evaluation metrics
│   ├── alembic/                         # Database migrations
│   ├── grafana/dashboards/              # Grafana dashboards
│   ├── prometheus/                      # Prometheus config
│   ├── scripts/                         # Utility scripts
│   ├── Dockerfile
│   ├── pyproject.toml                   # Python dependencies
│   └── alembic.ini                      # Alembic configuration
├── frontend/
│   ├── src/
│   │   ├── components/                 # Vue components
│   │   ├── composables/                 # Vue composables
│   │   ├── router/                      # Vue Router config
│   │   ├── services/                    # API services
│   │   ├── stores/                      # Pinia stores
│   │   ├── types/                       # TypeScript types
│   │   ├── views/                       # Vue views
│   │   ├── App.vue
│   │   └── main.ts
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── Makefile                             # Development commands
├── docker-compose.yml
├── docker-compose.monitoring.yml
└── README.md
```

## 🛡️ Security

For security concerns, please review our [Security Policy](SECURITY.md).

### Security Features

- **JWT Authentication**: Secure token-based authentication with configurable expiration
- **Password Hashing**: bcrypt-based password hashing
- **Input Sanitization**: All user inputs are sanitized and validated
- **Rate Limiting**: Protection against brute force and DDoS attacks
- **CORS Protection**: Configurable allowed origins
- **Protected Admin Actions**: Admin-only endpoints require special permissions

## 📄 License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

## 🤝 Contributing

Contributions are welcome! Please ensure:

1. Code follows the project's coding standards
2. All tests pass
3. New features include appropriate tests
4. Documentation is updated
5. Commit messages follow conventional commits format

## 📞 Support

For issues, questions, or contributions, please open an issue on the project repository.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework for building APIs
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Agent workflow orchestration
- [Langfuse](https://langfuse.com/) - LLM observability platform
- [Vue.js](https://vuejs.org/) - Progressive JavaScript framework
- [Naive UI](https://www.naiveui.com/) - Vue 3 component library
