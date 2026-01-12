#!/bin/bash

# Replit 优化启动脚本
echo "🚀 Starting TextLingo2 API on Replit..."

# 设置环境变量
export PYTHONPATH="/home/runner/$REPL_SLUG/api:$PYTHONPATH"
export PYTHONUNBUFFERED=1

# 检查并安装依赖
echo "📦 Installing dependencies..."
pip install --no-cache-dir -r requirements.txt

# 检查关键环境变量
if [ -z "$SUPABASE_URL" ]; then
    echo "⚠️  Warning: SUPABASE_URL not set"
fi

if [ -z "$JWT_SECRET_KEY" ]; then
    echo "⚠️  Warning: JWT_SECRET_KEY not set"
fi

# 启动应用
echo "🌟 Starting FastAPI server on port ${PORT:-8000}..."
python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers 1 \
    --access-log \
    --log-level info