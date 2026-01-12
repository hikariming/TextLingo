#!/bin/bash

# TextLingo2 云平台单容器部署启动脚本
# 适用于 Railway, Replit, Heroku 等单容器限制的平台
# 在单个容器中同时运行 API 服务和 Celery Worker

set -e

echo "🌐 TextLingo2 云平台部署启动脚本"
echo "=================================="

# 设置环境变量
export PYTHONPATH="/app:$PYTHONPATH"
export PYTHONUNBUFFERED=1

# 检查必需的环境变量
echo "🔍 检查环境配置..."

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
        exit 1
    fi
done

echo "✅ 基础环境变量检查通过"

# 检查 Redis 配置
CELERY_ENABLED=false
if [ -n "$REDIS_URL" ] || [ -n "$CELERY_BROKER_URL" ]; then
    echo "🔍 检查 Redis 连接..."
    
    REDIS_TEST_URL="${CELERY_BROKER_URL:-$REDIS_URL}"
    
    if python -c "
import redis
import sys
try:
    r = redis.from_url('$REDIS_TEST_URL')
    r.ping()
    print('✅ Redis 连接成功')
    sys.exit(0)
except Exception as e:
    print(f'❌ Redis 连接失败: {e}')
    sys.exit(1)
" 2>/dev/null; then
        CELERY_ENABLED=true
        echo "✅ Celery 功能启用"
    else
        echo "⚠️  Redis 连接失败，Celery 功能禁用"
        echo "   后台任务 (Anki导入、AI文章讲解) 将不可用"
    fi
else
    echo "⚠️  未配置 Redis，Celery 功能禁用"
    echo "   请配置 REDIS_URL 或 CELERY_BROKER_URL 以启用后台任务"
fi

echo ""
echo "🚀 启动服务..."

# 创建 supervisor 配置 (如果需要同时运行多个进程)
if [ "$CELERY_ENABLED" = true ]; then
    echo "📋 启动模式: API + Celery Worker"
    
    # 在后台启动 Celery Worker
    echo "🔄 启动 Celery Worker..."
    celery -A app.core.celery_app worker \
        --loglevel=info \
        --queues=file_processing,ai_processing \
        --concurrency=1 \
        --prefetch-multiplier=1 &
    
    CELERY_PID=$!
    echo "   Celery Worker PID: $CELERY_PID"
    
    # 等待 Celery 启动
    sleep 3
    
    # 启动 API 服务 (前台)
    echo "🌟 启动 API 服务..."
    echo "📚 服务地址: http://0.0.0.0:${PORT:-8000}"
    echo "🔧 功能状态:"
    echo "  ✅ API 服务: 可用"
    echo "  ✅ 后台任务: 可用 (Anki导入、AI文章讲解)"
    echo ""
    
    # 设置信号处理，确保退出时清理 Celery 进程
    trap 'echo "🛑 停止服务..."; kill $CELERY_PID 2>/dev/null; exit' INT TERM
    
    # 启动 API
    exec python -m uvicorn app.main:app \
        --host 0.0.0.0 \
        --port ${PORT:-8000} \
        --workers 1 \
        --access-log
else
    echo "📋 启动模式: 仅 API (Celery 禁用)"
    echo "🌟 启动 API 服务..."
    echo "📚 服务地址: http://0.0.0.0:${PORT:-8000}"
    echo "🔧 功能状态:"
    echo "  ✅ API 服务: 可用"
    echo "  ❌ 后台任务: 不可用 (需要配置 Redis)"
    echo "      - ❌ Anki 异步导入: 不可用"
    echo "      - ❌ AI 全局文章讲解: 不可用"
    echo ""
    echo "💡 要启用后台任务功能，请："
    echo "   1. 配置 REDIS_URL 环境变量"
    echo "   2. 重新部署服务"
    echo ""
    
    # 启动 API (仅API模式)
    exec python -m uvicorn app.main:app \
        --host 0.0.0.0 \
        --port ${PORT:-8000} \
        --workers 1 \
        --access-log
fi 