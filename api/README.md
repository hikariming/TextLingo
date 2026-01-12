# TextLingo2 后端API

基于 FastAPI 和 Supabase 构建的高性能语言学习平台后端服务。

## 🚀 功能特性

- **用户认证**: 基于 Supabase Auth 的用户注册、登录、JWT 令牌验证
- **异步任务处理**: 使用 Celery + Redis 处理耗时任务（AI 分析、Anki 导入等）
- **API 文档**: 自动生成的 Swagger/OpenAPI 文档
- **Docker 支持**: 容器化部署，开发环境一键启动
- **结构化日志**: 使用 structlog 进行日志记录

## 📋 技术栈

- **框架**: FastAPI 0.104+
- **数据库**: Supabase (PostgreSQL)
- **认证**: Supabase Auth + JWT
- **任务队列**: Celery + Redis
- **容器化**: Docker + Docker Compose
- **数据验证**: Pydantic

## 🛠️ 快速开始

### 1. 环境配置

**方法一：使用快速配置脚本（推荐）**
```bash
./setup_env.sh
```

**方法二：手动配置**
```bash
# 复制环境变量示例文件
cp env.example .env

# 编辑配置文件
nano .env  # 或使用您喜欢的编辑器
```

环境变量示例文件 `env.example` 包含了所有必需的配置项和详细说明。

### 2. 获取 Supabase 配置

1. 访问 [Supabase Dashboard](https://supabase.com/dashboard)
2. 创建新项目或选择现有项目
3. 在项目设置中找到 API 配置：
   - `SUPABASE_URL`: 项目 URL
   - `SUPABASE_ANON_KEY`: 匿名公钥
   - `SUPABASE_SERVICE_ROLE_KEY`: 服务角色密钥

### 3. 生成安全密钥

```bash
# 快速生成所需的密钥
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)"
echo "SECRET_KEY=$(openssl rand -hex 32)"
```

将生成的密钥复制到 `.env` 文件中对应的位置。

### 4. 使用 Docker Compose 启动

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f api

# 停止服务
docker-compose down
```

### 5. 本地开发模式

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 Redis (需要单独安装)
redis-server

# 启动 API 服务
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 启动 Celery Worker (新终端)
celery -A app.core.celery_app worker --loglevel=info

# 启动 Celery Flower 监控 (可选)
celery -A app.core.celery_app flower --port=5555
```

## 📚 API 文档

启动服务后，访问以下地址查看 API 文档：

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **健康检查**: http://localhost:8000/health

## 🔗 API 端点

### 认证相关

- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录  
- `GET /api/v1/auth/me` - 获取当前用户信息
- `POST /api/v1/auth/logout` - 用户登出

### 示例请求

#### 用户注册
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "password": "your-password",
       "full_name": "Your Name"
     }'
```

#### 用户登录
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com", 
       "password": "your-password"
     }'
```

#### 获取用户信息
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
     -H "Authorization: Bearer your-access-token"
```

## 🏗️ 项目结构

```
api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── auth.py          # 认证端点
│   │       └── api_router.py        # API 路由
│   ├── core/
│   │   ├── config.py               # 配置管理
│   │   ├── dependencies.py         # FastAPI 依赖项
│   │   └── celery_app.py          # Celery 配置
│   ├── schemas/
│   │   └── auth.py                 # 数据模型
│   ├── services/
│   │   ├── auth_service.py         # 认证服务
│   │   └── supabase_client.py      # Supabase 客户端
│   ├── tasks/
│   │   ├── analyze_text.py         # AI 分析任务
│   │   └── process_anki.py         # Anki 处理任务
│   └── main.py                     # 应用入口
├── docker-compose.yml              # Docker 编排
├── Dockerfile                      # Docker 镜像
├── requirements.txt               # Python 依赖
└── README.md                      # 项目说明
```

## 🔧 开发指南

### 添加新的 API 端点

1. 在 `app/schemas/` 中定义数据模型
2. 在 `app/services/` 中实现业务逻辑
3. 在 `app/api/v1/endpoints/` 中创建端点
4. 在 `app/api/v1/api_router.py` 中注册路由

### 添加异步任务

1. 在 `app/tasks/` 中定义任务函数
2. 使用 `@celery_app.task` 装饰器
3. 在业务逻辑中调用 `task_name.delay()`

## 🚀 部署

### 生产环境配置

1. 设置 `DEBUG=false`
2. 使用强密钥和随机密码
3. 配置适当的 CORS 域名
4. 使用 HTTPS
5. 配置日志聚合
6. 设置监控和告警

### 推荐部署方案

- **云服务**: Google Cloud Run, AWS Lambda, Azure Container Instances
- **VPS**: 使用 Docker Compose 在 DigitalOcean, Vultr 等平台部署
- **Kubernetes**: 使用 K8s 进行大规模部署

## 📝 License

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！ 