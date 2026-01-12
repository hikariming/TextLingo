#!/bin/bash

# TextLingo2 后端开发环境启动脚本
# Mac 兼容版本 - 支持 Conda 环境管理

set -e

# 配置变量
CONDA_ENV_NAME="textlingo2"
PYTHON_VERSION="3.11"
PROJECT_NAME="TextLingo2"

# Mac 兼容性检查
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 检测到 macOS 系统"
fi

echo "🚀 启动 ${PROJECT_NAME} 后端开发环境"
echo "================================"

# 显示当前 conda 状态
if command -v conda &> /dev/null; then
    echo "📋 当前 Conda 信息:"
    CURRENT_ENV=$(conda info --envs | grep '*' | awk '{print $1}')
    if [ "$CURRENT_ENV" ]; then
        echo "  激活环境: $CURRENT_ENV"
    else
        echo "  激活环境: base"
    fi
    
    if conda env list | grep -q "^${CONDA_ENV_NAME} "; then
        echo "  项目环境: ✅ ${CONDA_ENV_NAME} (已存在)"
    else
        echo "  项目环境: ❌ ${CONDA_ENV_NAME} (未创建)"
    fi
    echo ""
fi

# 检查并设置 Conda 环境
check_and_setup_conda() {
    echo "🐍 检查 Conda 环境..."
    
    # 检查 conda 是否安装
    if ! command -v conda &> /dev/null; then
        echo "❌ 未找到 Conda"
        echo "请先安装 Miniconda 或 Anaconda："
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "  方式1: 官网下载 https://docs.conda.io/en/latest/miniconda.html"
            echo "  方式2: 使用 Homebrew: brew install --cask miniconda"
        else
            echo "  请访问: https://docs.conda.io/en/latest/miniconda.html"
        fi
        exit 1
    fi
    
    # 初始化 conda (确保在脚本中可用)
    # 检查多种可能的 conda 安装路径
    CONDA_PATHS=(
        "$HOME/miniconda3/etc/profile.d/conda.sh"
        "$HOME/anaconda3/etc/profile.d/conda.sh"
        "/opt/conda/etc/profile.d/conda.sh"
        "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh"
        "/usr/local/Caskroom/miniconda/base/etc/profile.d/conda.sh"
        "/opt/miniconda3/etc/profile.d/conda.sh"
        "/usr/local/miniconda3/etc/profile.d/conda.sh"
    )
    
    CONDA_INITIALIZED=false
    for conda_path in "${CONDA_PATHS[@]}"; do
        if [ -f "$conda_path" ]; then
            echo "🔄 使用 conda 配置: $conda_path"
            source "$conda_path"
            CONDA_INITIALIZED=true
            break
        fi
    done
    
    # 如果都没找到，尝试通过 conda info 获取路径
    if [ "$CONDA_INITIALIZED" = false ]; then
        echo "⚠️  未找到标准 conda 配置文件，尝试自动检测..."
        if command -v conda &> /dev/null; then
            CONDA_BASE=$(conda info --base 2>/dev/null)
            if [ -n "$CONDA_BASE" ] && [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
                echo "🔄 使用检测到的 conda 配置: $CONDA_BASE/etc/profile.d/conda.sh"
                source "$CONDA_BASE/etc/profile.d/conda.sh"
                CONDA_INITIALIZED=true
            fi
        fi
    fi
    
    if [ "$CONDA_INITIALIZED" = false ]; then
        echo "❌ 无法初始化 conda"
        echo "请确保 conda 已正确安装并运行: conda init"
        echo "然后重新启动终端"
        exit 1
    fi
    
    # 检查环境是否存在
    if conda env list | grep -q "^${CONDA_ENV_NAME} "; then
        echo "✅ 发现现有的 ${CONDA_ENV_NAME} 环境"
    else
        echo "🔧 创建新的 ${CONDA_ENV_NAME} 环境..."
        
        # 检查是否存在 environment.yml
        if [ -f "environment.yml" ]; then
            echo "📋 使用 environment.yml 创建环境..."
            conda env create -f environment.yml
        else
            echo "🐍 创建基础 Python ${PYTHON_VERSION} 环境..."
            conda create -n "${CONDA_ENV_NAME}" python="${PYTHON_VERSION}" -y
        fi
        echo "✅ 环境创建完成"
    fi
    
    # 激活环境
    echo "🔄 激活 ${CONDA_ENV_NAME} 环境..."
    conda activate "${CONDA_ENV_NAME}"
    
    # 验证 Python 版本
    CURRENT_PYTHON_VERSION=$(python --version | cut -d' ' -f2)
    echo "🐍 当前 Python 版本: ${CURRENT_PYTHON_VERSION}"
    
    # 使用 Python 自身进行版本比较
    PYTHON_VERSION_CHECK=$(python -c "
import sys
major, minor = sys.version_info[:2]
if major >= 3 and minor >= 10:
    print('OK')
else:
    print('LOW')
")
    
    if [[ "$PYTHON_VERSION_CHECK" == "OK" ]]; then
        echo "✅ Python 版本检查通过"
    else
        echo "⚠️  Python 版本较低，建议使用 3.10 或更高版本"
    fi
}

# 检查 Celery 连接
check_celery_connection() {
    echo "🔍 检查 Celery 连接..."
    
    if [ -z "$REDIS_URL" ] && [ -z "$CELERY_BROKER_URL" ]; then
        echo "⚠️  未配置 Redis 连接，Celery 功能将不可用"
        echo "   请在 .env 文件中配置 REDIS_URL 或 CELERY_BROKER_URL"
        return 1
    fi
    
    # 尝试连接 Redis
    local redis_url="${CELERY_BROKER_URL:-$REDIS_URL}"
    echo "   正在测试连接: $redis_url"
    
    # 使用 Python 简单测试 Redis 连接
    python -c "
import redis
import sys
try:
    r = redis.from_url('$redis_url')
    r.ping()
    print('✅ Redis 连接成功')
    sys.exit(0)
except Exception as e:
    print(f'❌ Redis 连接失败: {e}')
    sys.exit(1)
" 2>/dev/null
    
    return $?
}

# 更新依赖包
update_dependencies() {
    echo "📦 更新和安装 Python 依赖..."
    
    # 先升级 pip
    python -m pip install --upgrade pip
    
    # 检查是否有 requirements.txt
    if [ -f "requirements.txt" ]; then
        echo "  使用 requirements.txt 安装依赖..."
        pip install -r requirements.txt
    else
        echo "  手动安装核心依赖..."
        
        # 安装核心框架
        echo "    安装核心框架..."
        pip install fastapi==0.104.1 uvicorn[standard]==0.24.0
        
        # 安装数据库相关 (让 supabase 自动处理其依赖)
        echo "    安装数据库相关..."
        pip install supabase==2.7.4 sqlalchemy[asyncio]==2.0.23 asyncpg==0.29.0
        
        # 安装认证和安全
        echo "    安装认证和安全..."
        pip install python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4 python-multipart==0.0.6
        
        # 安装异步任务
        echo "    安装异步任务..."
        pip install celery==5.3.4 redis==5.0.1
        
        # 安装其他工具
        echo "    安装其他工具..."
        pip install 'pydantic==2.5.0' 'pydantic-settings==2.1.0' 'httpx>=0.26.0,<0.29.0' structlog==23.2.0 python-dotenv==1.0.0
        
        # 安装开发工具
        echo "    安装开发工具..."
        pip install pytest==7.4.3 pytest-asyncio==0.21.1 black==23.11.0 isort==5.12.0
    fi
    
    echo "✅ 依赖安装完成"
}

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 文件"
    echo "请根据 README.md 中的说明创建 .env 文件"
    exit 1
fi

echo "📋 检查环境配置..."

# 安全地加载 .env 文件
if [ -f ".env" ]; then
    set -a  # 自动导出变量
    source .env
    set +a  # 关闭自动导出
else
    echo "❌ 未找到 .env 文件"
    echo "正在从 env.example 创建 .env 文件..."
    cp env.example .env
    echo "✅ 已创建 .env 文件"
    echo "⚠️  请编辑 .env 文件，填入正确的配置值"
    echo "📝 特别注意配置："
    echo "   - SUPABASE_URL"
    echo "   - SUPABASE_ANON_KEY" 
    echo "   - SUPABASE_SERVICE_ROLE_KEY"
    echo "   - JWT_SECRET_KEY (运行: openssl rand -hex 32)"
    echo "   - SECRET_KEY (运行: openssl rand -hex 32)"
    echo "   - Redis 配置 (推荐使用 Upstash)"
    echo ""
    echo "配置完成后请重新运行此脚本"
    exit 1
fi

# 检查必需的环境变量
REQUIRED_VARS=(
    "SUPABASE_URL"
    "SUPABASE_ANON_KEY" 
    "SUPABASE_SERVICE_ROLE_KEY"
    "JWT_SECRET_KEY"
    "SECRET_KEY"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ 缺少必需的环境变量: $var"
        echo "请检查 .env 文件配置"
        exit 1
    fi
done

echo "✅ 环境配置检查通过"

# 选择启动方式
echo ""
echo "请选择启动方式："
echo "1) Docker Compose (推荐 - 包含 API + Celery + Redis)"
echo "2) Conda 本地开发模式 (API + Celery 手动启动)"
echo "3) Conda API + Celery 一键启动 (推荐本地开发)"
echo "4) Conda API 服务 (仅API，不包含 Celery)"
echo "5) Conda Celery Worker (仅启动 Celery Worker)"
echo "6) 运行测试"
echo "7) 更新 Conda 环境"
echo "8) 重新创建 Conda 环境"

read -p "请输入选择 (1-8): " choice

case $choice in
    1)
        echo "🐳 启动 Docker Compose..."
        if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
            echo "❌ 未找到 Docker 或 Docker Compose"
            echo "请先安装 Docker 和 Docker Compose"
            exit 1
        fi
        
        # 检查是否有 docker compose 或 docker-compose
        if command -v docker &> /dev/null && docker compose version &> /dev/null; then
            DOCKER_COMPOSE_CMD="docker compose"
        elif command -v docker-compose &> /dev/null; then
            DOCKER_COMPOSE_CMD="docker-compose"
        else
            echo "❌ 未找到 docker compose 命令"
            exit 1
        fi
        
        echo "构建并启动服务..."
        $DOCKER_COMPOSE_CMD up --build -d
        
        echo ""
        echo "🎉 服务启动成功！"
        echo ""
        echo "📚 访问地址："
        echo "  - API 文档: http://localhost:8000/api/v1/docs"
        echo "  - 健康检查: http://localhost:8000/health"
        echo "  - Celery 监控: http://localhost:5555"
        echo ""
        echo "📝 查看日志："
        echo "  $DOCKER_COMPOSE_CMD logs -f api"
        echo ""
        echo "🛑 停止服务："
        echo "  $DOCKER_COMPOSE_CMD down"
        ;;
        
    2)
        echo "💻 启动 Conda 本地开发模式..."
        
        # 设置 conda 环境
        check_and_setup_conda
        
        # 检查 Redis 连接
        if check_celery_connection; then
            CELERY_AVAILABLE=true
        else
            CELERY_AVAILABLE=false
        fi
        
        # 更新依赖
        update_dependencies
        
        echo "🧹 清理旧进程..."
        # 杀死可能存在的 API 进程
        pkill -f "uvicorn app.main:app" 2>/dev/null || true
        sleep 1
        
        # 启动服务
        echo "🚀 启动 API 服务..."
        echo ""
        echo "💡 重要提示: 为了使用 Anki 导入功能，请在新终端中启动 Celery Worker:"
        echo "  ${BASH_SOURCE[0]} 然后选择选项 4"
        echo ""
        echo "或者手动运行："
        echo "  conda activate ${CONDA_ENV_NAME}"
        echo "  cd $(pwd)"
        echo "  export PYTHONPATH=\"\${PWD}:\${PYTHONPATH}\""
        echo "  celery -A app.core.celery_app worker --loglevel=info --queues=file_processing,ai_processing"
        echo ""
        echo "📚 服务地址:"
        echo "  - API 文档: http://localhost:8000/api/v1/docs"
        echo "  - 健康检查: http://localhost:8000/health"
        echo ""
        echo "🔧 Celery 功能状态:"
        if [ "$CELERY_AVAILABLE" = true ]; then
            echo "  ✅ 异步 Anki 导入: 可用 (需要启动 Celery Worker)"
            echo "  ✅ AI 文本分析: 可用 (需要启动 Celery Worker)"
            echo "  💡 启动 Worker: 运行此脚本选择选项 4"
        else
            echo "  ❌ 异步 Anki 导入: 不可用 (Redis 连接失败)"
            echo "  ❌ AI 文本分析: 不可用 (Redis 连接失败)"
            echo "  💡 修复方法: 检查 .env 中的 Redis 配置"
        fi
        echo ""
        echo "🛑 停止服务: Ctrl+C"
        echo "================================"
        # 设置 PYTHONPATH 确保可以找到 app 模块
        export PYTHONPATH="${PWD}:${PYTHONPATH}"
        python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        ;;
        
    3)
        echo "🚀 启动 Conda API + Celery 一键启动..."
        
        # 设置 conda 环境
        check_and_setup_conda
        
        # 检查 Redis 连接
        if ! check_celery_connection; then
            echo ""
            echo "推荐免费 Redis 服务："
            echo "  - Upstash: https://console.upstash.com"
            echo "  - Redis Cloud: https://redis.com/try-free"
            echo "  - Railway: https://railway.app"
            exit 1
        fi
        
        # 更新依赖
        update_dependencies
        
        echo "🧹 清理旧进程..."
        # 杀死可能存在的 API 和 Celery 进程
        pkill -f "uvicorn app.main:app" 2>/dev/null || true
        pkill -f "celery.*app.core.celery_app.*worker" 2>/dev/null || true
        
        # 等待进程完全结束
        sleep 2
        
        echo "🎯 使用一键启动脚本..."
        echo "此模式将同时启动 API 服务和 Celery Worker"
        echo ""
        exec ./start_celery_and_api.sh
        ;;
        
    4)
        echo "⚡ 启动 Conda API 服务 (仅API，不包含 Celery)..."
        
        # 设置 conda 环境
        check_and_setup_conda
        
        # 更新依赖
        update_dependencies
        
        echo "🧹 清理旧进程..."
        # 杀死可能存在的 API 进程
        pkill -f "uvicorn app.main:app" 2>/dev/null || true
        sleep 1
        
        echo "🚀 启动 API 服务..."
        echo ""
        echo "⚠️  注意: 此模式不包含 Celery Worker，以下功能将不可用:"
        echo "  ❌ 异步 Anki 导入 (会返回错误)"
        echo "  ❌ AI 长文本分析 (会返回错误)"
        echo "  ❌ 批量文本处理 (会返回错误)"
        echo ""
        echo "💡 如需完整功能，请选择选项 1 (Docker) 或 2 (本地开发模式)"
        echo ""
        echo "📚 服务地址:"
        echo "  - API 文档: http://localhost:8000/api/v1/docs"
        echo "  - 健康检查: http://localhost:8000/health"
        echo ""
        echo "🛑 停止服务: Ctrl+C"
        echo "================================"
        # 设置 PYTHONPATH 确保可以找到 app 模块
        export PYTHONPATH="${PWD}:${PYTHONPATH}"
        python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        ;;
        
    5)
        echo "🔄 启动 Conda Celery Worker..."
        
        # 设置 conda 环境
        check_and_setup_conda
        
        # 检查 Redis 连接
        if ! check_celery_connection; then
            echo ""
            echo "推荐免费 Redis 服务："
            echo "  - Upstash: https://console.upstash.com"
            echo "  - Redis Cloud: https://redis.com/try-free"
            echo "  - Railway: https://railway.app"
            echo ""
            echo "配置示例 (.env 文件)："
            echo "  REDIS_URL=redis://your-redis-url:6379"
            echo "  CELERY_BROKER_URL=redis://your-redis-url:6379"
            echo "  CELERY_RESULT_BACKEND=redis://your-redis-url:6379"
            exit 1
        fi
        
        echo "   Broker URL: ${CELERY_BROKER_URL:-$REDIS_URL}"
        echo "   Result Backend: ${CELERY_RESULT_BACKEND:-$REDIS_URL}"
        
        # 更新依赖
        update_dependencies
        
        echo "🧹 清理旧进程..."
        # 杀死可能存在的 Celery Worker 进程
        pkill -f "celery.*app.core.celery_app.*worker" 2>/dev/null || true
        sleep 2
        
        echo "🚀 启动 Celery Worker..."
        echo ""
        echo "📋 Worker 配置:"
        echo "  - 队列: file_processing, ai_processing"
        echo "  - 日志级别: info"
        echo "  - 预取倍数: 1 (适合内存密集型任务)"
        echo ""
        echo "🔧 支持的任务:"
        echo "  ✅ process_anki.import_anki_package - Anki 包异步导入"
        echo "  ✅ ai_tasks.long_text_analysis - AI 长文本分析"
        echo "  ✅ ai_tasks.batch_text_processing - 批量文本处理"
        echo ""
        echo "🛑 停止 Worker: Ctrl+C"
        echo "================================"
        # 设置 PYTHONPATH 确保可以找到 app 模块
        export PYTHONPATH="${PWD}:${PYTHONPATH}"
        celery -A app.core.celery_app worker \
            --loglevel=info \
            --queues=file_processing,ai_processing \
            --concurrency=2 \
            --prefetch-multiplier=1
        ;;
        
    6)
        echo "🧪 运行 API 测试..."
        
        # 设置 conda 环境
        check_and_setup_conda
        
        # 安装测试依赖
        pip install requests
        
        python test_api.py
        ;;
        
    7)
        echo "🔄 更新 Conda 环境..."
        
        # 设置 conda 环境
        check_and_setup_conda
        
        # 强制更新依赖
        update_dependencies
        
        echo "✅ 环境更新完成！"
        echo "💡 现在可以选择其他启动选项"
        ;;
        
    8)
        echo "♻️  重新创建 Conda 环境..."
        
        # 检查并删除现有环境
        if conda env list | grep -q "^${CONDA_ENV_NAME} "; then
            echo "🗑️  删除现有环境 ${CONDA_ENV_NAME}..."
            conda env remove -n "${CONDA_ENV_NAME}" -y
        fi
        
        # 重新创建环境
        if [ -f "environment.yml" ]; then
            echo "📋 从 environment.yml 创建环境..."
            conda env create -f environment.yml
        else
            echo "🐍 创建基础环境..."
            conda create -n "${CONDA_ENV_NAME}" python="${PYTHON_VERSION}" -y
            
            # 激活环境并安装依赖
            conda activate "${CONDA_ENV_NAME}"
            update_dependencies
        fi
        
        echo "✅ 环境重新创建完成！"
        echo "💡 现在可以选择其他启动选项"
        ;;
        
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac 