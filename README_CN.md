# TerraChatBi

一个生产级的全栈 AI Agent 应用，采用 FastAPI 后端和 Vue 3 前端，集成 LangGraph 实现智能聊天机器人工作流。

## 🌟 特性

- **生产级架构**

  - FastAPI 后端，采用 uvloop 优化，提供高性能异步 API 端点
  - Vue 3 + Vite 前端，搭配 Naive UI 组件库和 TailwindCSS
  - LangGraph 集成，实现带状态持久化的 AI Agent 工作流
  - Langfuse 提供 LLM 可观测性和监控
  - 使用 structlog 进行结构化日志记录，支持环境特定格式化
  - 可配置的端点级限流保护
  - PostgreSQL + pgvector 实现数据持久化和向量存储
  - Docker 和 Docker Compose 支持，便于部署
  - Prometheus 指标和 Grafana 仪表盘监控

- **AI 与 LLM 功能**

  - 基于 mem0ai 和 pgvector 的长期记忆，实现语义记忆存储
  - 多供应商 LLM 支持（OpenAI、Azure OpenAI、VLLM、自定义端点）
  - LLM 服务支持自动重试逻辑和备份模型降级
  - 动态 AI 模型管理，支持数据库配置
  - 流式响应，实现实时聊天交互
  - 工具调用和函数执行能力

- **安全性**

  - 基于 JWT 的身份认证，支持会话管理
  - 基于工作空间的多租户支持
  - 基于角色的访问控制（RBAC）
  - 输入清洗和验证
  - CORS 配置
  - 限流保护

- **开发者体验**

  - 环境特定配置，自动加载 .env 文件
  - 完善的日志系统，支持上下文绑定
  - 清晰的项目结构，遵循最佳实践
  - 全面的类型提示，提供更好的 IDE 支持
  - 使用 Makefile 命令简化本地开发
  - 使用 Alembic 自动进行数据库迁移

- **模型评估框架**
  - 基于指标的自动化模型输出评估
  - 集成 Langfuse 进行追踪分析
  - 详细的 JSON 报告，包含成功/失败指标
  - 交互式命令行界面
  - 可自定义评估指标

## 🚀 快速开始

### 前置条件

- Python 3.13+
- Node.js 20.19.0+ 或 22.12.0+
- 带有 pgvector 扩展的 PostgreSQL
- Docker 和 Docker Compose（可选）

### 环境配置

1. 克隆仓库：

```bash
git clone <repository-url>
cd TerraAgent
```

2. 配置后端：

```bash
cd backend
uv sync
cp .env.example .env.development
```

3. 配置前端：

```bash
cd ../frontend
npm install
cp .env.example .env
```

4. 更新 `.env` 文件中的配置信息

### 数据库配置

1. 创建带有 pgvector 扩展的 PostgreSQL 数据库
2. 在 `.env` 文件中更新数据库连接配置：

```bash
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=terra-agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

数据库表会在应用启动时通过 Alembic 迁移自动创建。

### 运行应用

#### 本地开发

**后端：**

```bash
# 从项目根目录
make backend-dev
# 或从 backend 目录
cd backend && uv run uvicorn app.main:app --reload --port 8000 --loop uvloop
```

**前端：**

```bash
# 从项目根目录
make frontend-dev
# 或从 frontend 目录
cd frontend && npm run dev
```

访问应用：

- 前端：http://localhost:5173
- 后端 API：http://localhost:8000
- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

#### 使用 Docker

```bash
# 构建并运行后端 Docker 容器
make backend-docker-build-env ENV=development
make backend-docker-run-env ENV=development

# 构建并运行前端 Docker 容器
make frontend-docker-build
make frontend-docker-up
```

#### 监控服务

```bash
# 启动监控服务（Prometheus + Grafana）
make backend-monitoring-up

# 访问监控
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

Docker 部署包含：

- FastAPI 应用
- PostgreSQL 数据库
- Prometheus 指标收集
- Grafana 指标可视化
- 预配置的 API 性能和系统监控仪表盘

## 📊 模型评估

项目包含完善的评估框架，用于测量和追踪模型性能。评估器会自动从 Langfuse 获取追踪数据，应用评估指标，并生成详细报告。

### 运行评估

使用 Makefile 命令运行评估：

```bash
# 交互模式，逐步提示
make backend-eval [ENV=development|staging|production]

# 快速模式，使用默认设置（无提示）
make backend-eval-quick [ENV=development|staging|production]

# 评估但不生成报告
make backend-eval-no-report [ENV=development|staging|production]
```

### 评估功能

- **交互式 CLI**：友好的用户界面，带彩色输出和进度条
- **灵活配置**：可设置默认值或运行时自定义
- **详细报告**：JSON 报告包含全面的指标：
  - 整体成功率
  - 各指标性能表现
  - 持续时间和时间信息
  - 追踪级别的成功/失败详情

### 自定义指标

评估指标定义在 `evals/metrics/prompts/` 目录下的 markdown 文件中：

1. 在 prompts 目录创建新的 markdown 文件（如 `my_metric.md`）
2. 定义评估标准和评分逻辑
3. 评估器会自动发现并应用您的新指标

### 查看报告

报告自动生成在 `evals/reports/` 目录，文件名包含时间戳：

```
evals/reports/evaluation_report_YYYYMMDD_HHMMSS.json
```

每个报告包含：

- 高级统计数据（总追踪数、成功率等）
- 各指标性能指标
- 详细的追踪级别信息，便于调试

## 🔧 配置

应用使用灵活的配置系统，支持环境特定设置：

- `.env.development` - 本地开发设置
- `.env.staging` - 预发布环境设置
- `.env.production` - 生产环境设置

### 环境变量

```bash
# 应用配置
PROJECT_NAME="TerraChatBi"
APP_ENV=development

# 数据库
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=terra-agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Langfuse（LLM 可观测性）
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com

# JWT 配置
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_DAYS=30
DEFAULT_PWD="Terra@123456"

# 缓存设置
CACHE_TYPE=memory
# CACHE_REDIS_URL=redis://localhost:6379/0

# 限流配置
RATE_LIMIT_DEFAULT=["200 per day", "50 per hour"]
RATE_LIMIT_CHAT="30 per minute"
RATE_LIMIT_CHAT_STREAM="20 per minute"
```

## 🧠 长期记忆

应用包含由 mem0ai 和 pgvector 驱动的复杂长期记忆系统：

### 功能特性

- **语义记忆存储**：基于语义相似度存储和检索记忆
- **用户专属记忆**：每个用户拥有独立的记忆空间
- **自动记忆管理**：自动提取、存储和检索记忆
- **向量搜索**：使用 pgvector 进行高效的相似度搜索
- **可配置模型**：支持独立的记忆处理和嵌入模型

### 工作原理

1. **记忆添加**：在对话过程中，重要信息会被自动提取并存储
2. **记忆检索**：根据对话上下文检索相关记忆
3. **记忆搜索**：语义搜索可在对话间查找相关记忆
4. **记忆更新**：新信息可用时更新现有记忆

## 🤖 LLM 服务

LLM 服务提供稳健的、生产级的大语言模型交互，支持自动重试逻辑和多供应商支持。

### 功能特性

- **多供应商支持**：OpenAI、Azure OpenAI、VLLM 以及自定义 OpenAI 兼容端点
- **动态模型配置**：通过数据库配置 AI 模型，支持运行时切换
- **自动重试**：使用 tenacity 实现指数退避重试逻辑
- **备份模型降级**：主模型失败时自动降级到备份模型
- **流式支持**：实时流式响应，用于聊天交互

### 支持的供应商

| 供应商 | 使用场景 | 配置方式 |
| ------ | -------- | -------- |
| OpenAI | 生产工作负载 | API key + base URL |
| Azure OpenAI | 企业部署 | Azure endpoint + deployment name |
| VLLM | 自托管模型 | 自定义端点 URL |
| 自定义 | OpenAI 兼容 API | 任意兼容端点 |

### 模型管理

通过管理 API 管理 AI 模型：

- `POST /api/v1/system/aimodel` - 注册新的 AI 模型
- `GET /api/v1/system/aimodel` - 列出所有模型
- `PUT /api/v1/system/aimodel/default/{id}` - 设置默认模型
- `PUT /api/v1/system/aimodel/backup/{id}` - 设置备份模型
- `POST /api/v1/system/aimodel/status` - 测试模型连通性

### 重试配置

- API 超时、限流和临时错误时自动重试
- **最大尝试次数**：2
- **等待策略**：指数退避（1s, 2s, 4s）
- **日志记录**：所有重试尝试都带上下文记录

## 📝 高级日志

应用使用 structlog 进行结构化、带上下文的日志记录，支持自动请求追踪。

### 功能特性

- **结构化日志**：所有日志都是带有一致字段的结构化格式
- **请求上下文**：自动绑定 request_id、session_id 和 user_id
- **环境特定格式化**：生产环境使用 JSON，开发环境使用彩色控制台
- **性能追踪**：自动记录请求持续时间和状态
- **异常追踪**：保留上下文的完整堆栈跟踪

### 日志上下文中间件

每个请求自动获取：

- 唯一请求 ID
- 会话 ID（如已认证）
- 用户 ID（如已认证）
- 请求路径和方法
- 响应状态和持续时间

### 日志格式标准

- **事件名称**：lowercase_with_underscores（小写下划线格式）
- **禁用 F-Strings**：将变量作为 kwargs 传递，便于过滤
- **上下文绑定**：始终包含相关 ID 和上下文
- **适当的级别**：debug、info、warning、error、exception

## ⚡ 性能优化

### uvloop 集成

应用通过 Makefile 自动启用 uvloop 以增强异步性能：

**性能提升**：

- asyncio 操作速度提升 2-4 倍
- I/O 密集型任务延迟更低
- 更好的连接池管理
- 并发请求 CPU 使用率更低

### 连接池

- **数据库**：异步连接池，可配置池大小
- **LangGraph 检查点**：状态持久化共享连接池
- **Redis**（可选）：缓存连接池

### 缓存策略

- 仅缓存成功响应
- 根据数据波动性配置 TTL
- 更新时失效缓存
- 支持 Redis 或内存缓存

## 🔌 API 参考

### 认证端点

- `POST /api/v1/auth/login` - 认证并获取 JWT 令牌
- `POST /api/v1/auth/register` - 注册新用户（仅管理员）
- `PATCH /api/v1/auth/users/me/password` - 修改当前用户密码
- `PATCH /api/v1/auth/users/status` - 更新用户状态（仅管理员）
- `DELETE /api/v1/auth/users/{user_id}` - 删除用户（仅管理员）

### 用户管理端点

- `GET /api/v1/auth/users` - 获取所有用户（仅管理员）
- `GET /api/v1/auth/users/by-email` - 通过邮箱获取用户（仅管理员）

### 工作空间管理端点

- `POST /api/v1/auth/workspaces` - 创建新工作空间（仅管理员）
- `GET /api/v1/auth/workspaces` - 获取所有工作空间（仅管理员）
- `GET /api/v1/auth/workspaces/{workspace_id}` - 通过 ID 获取工作空间
- `DELETE /api/v1/auth/workspaces/{workspace_id}` - 删除工作空间
- `POST /api/v1/auth/workspaces/{workspace_id}/users` - 添加用户到工作空间
- `GET /api/v1/auth/workspaces/{workspace_id}/users` - 获取工作空间用户
- `PATCH /api/v1/auth/users/switch/workspace` - 切换当前工作空间

### AI 模型管理端点

- `POST /api/v1/system/aimodel` - 创建 AI 模型（仅管理员）
- `GET /api/v1/system/aimodel` - 列出所有 AI 模型
- `GET /api/v1/system/aimodel/{id}` - 通过 ID 获取 AI 模型
- `PUT /api/v1/system/aimodel` - 更新 AI 模型
- `DELETE /api/v1/system/aimodel/{id}` - 删除 AI 模型
- `PUT /api/v1/system/aimodel/default/{id}` - 设置默认模型
- `PUT /api/v1/system/aimodel/backup/{id}` - 设置备份模型
- `POST /api/v1/system/aimodel/status` - 测试模型连通性

### 聊天端点

- `POST /api/v1/chatbot/chat` - 发送消息并获取响应
- `POST /api/v1/chatbot/chat/stream` - 发送消息并获取流式响应
- `GET /api/v1/chatbot/messages` - 获取对话历史
- `DELETE /api/v1/chatbot/messages` - 清空对话历史

### 健康检查与监控

- `GET /` - 根端点，返回 API 信息
- `GET /health` - 健康检查，包含数据库状态
- `GET /metrics` - Prometheus 指标端点

详细的 API 文档请访问 `/docs`（Swagger UI）或 `/redoc`（ReDoc）。

## 📚 项目结构

```
TerraAgent/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py              # 认证与用户管理
│   │   │       ├── chatbot.py           # 聊天端点
│   │   │       ├── api.py               # API 路由聚合
│   │   │       └── system/
│   │   │           └── ai_model.py      # AI 模型管理
│   │   ├── core/
│   │   │   ├── common/
│   │   │   │   ├── config.py            # 配置管理
│   │   │   │   ├── logging.py           # 结构化日志
│   │   │   │   ├── metrics.py           # Prometheus 指标
│   │   │   │   ├── middleware/          # 自定义中间件
│   │   │   │   ├── cache.py             # 缓存层
│   │   │   │   ├── db.py                # 数据库工具
│   │   │   │   └── limiter.py           # 限流
│   │   │   ├── langgraph/
│   │   │   │   ├── graph.py             # LangGraph Agent
│   │   │   │   └── tools/               # Agent 工具
│   │   │   ├── llm/
│   │   │   │   └── model_factory.py     # LLM 工厂与供应商
│   │   │   └── prompts/                 # 系统提示词
│   │   ├── models/
│   │   │   ├── user.py                  # 用户与工作空间模型
│   │   │   ├── session.py               # 会话模型
│   │   │   └── ai_model.py              # AI 模型实体
│   │   ├── schemas/
│   │   │   ├── auth.py                  # 认证 Schema
│   │   │   ├── chat.py                  # 聊天 Schema
│   │   │   └── graph.py                 # 图状态 Schema
│   │   ├── services/
│   │   │   ├── auth.py                  # 认证服务
│   │   │   ├── llm.py                   # LLM 服务（含重试）
│   │   │   ├── database.py              # 数据库服务
│   │   │   └── system.py                # 系统服务
│   │   ├── utils/
│   │   │   ├── auth.py                  # 认证工具
│   │   │   ├── graph.py                 # 图工具
│   │   │   └── sanitization.py          # 输入清洗
│   │   └── main.py                      # 应用入口
│   ├── evals/
│   │   ├── evaluator.py                 # 评估逻辑
│   │   ├── main.py                      # 评估 CLI
│   │   └── metrics/prompts/             # 评估指标
│   ├── alembic/                         # 数据库迁移
│   ├── grafana/dashboards/              # Grafana 仪表盘
│   ├── prometheus/                      # Prometheus 配置
│   ├── scripts/                         # 工具脚本
│   ├── Dockerfile
│   ├── pyproject.toml                   # Python 依赖
│   └── alembic.ini                      # Alembic 配置
├── frontend/
│   ├── src/
│   │   ├── components/                 # Vue 组件
│   │   ├── composables/                 # Vue 组合式函数
│   │   ├── router/                      # Vue Router 配置
│   │   ├── services/                    # API 服务
│   │   ├── stores/                      # Pinia 状态管理
│   │   ├── types/                       # TypeScript 类型
│   │   ├── views/                       # Vue 视图
│   │   ├── App.vue
│   │   └── main.ts
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── Makefile                             # 开发命令
├── docker-compose.yml
├── docker-compose.monitoring.yml
└── README.md
```

## 🛡️ 安全

如有安全问题，请查看 [安全策略](SECURITY.md)。

### 安全特性

- **JWT 认证**：安全的基于令牌的认证，支持可配置过期时间
- **密码哈希**：基于 bcrypt 的密码哈希
- **输入清洗**：所有用户输入都经过清洗和验证
- **限流保护**：防止暴力破解和 DDoS 攻击
- **CORS 保护**：可配置的允许来源
- **管理员操作保护**：管理员专属端点需要特殊权限

## 📄 许可证

本项目采用 [LICENSE](LICENSE) 文件中指定的条款授权。

## 🤝 贡献

欢迎贡献！请确保：

1. 代码遵循项目的编码规范
2. 所有测试通过
3. 新功能包含适当的测试
4. 更新文档
5. 提交信息遵循约定式提交格式

## 📞 支持

如有问题、疑问或贡献，请在项目仓库提交 issue。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 构建 API 的现代 Web 框架
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Agent 工作流编排
- [Langfuse](https://langfuse.com/) - LLM 可观测性平台
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Naive UI](https://www.naiveui.com/) - Vue 3 组件库
