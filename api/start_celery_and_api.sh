#!/bin/bash

# TextLingo2 API 启动脚本
# 用于本地开发环境

set -e

CONDA_ENV_NAME="textlingo2"

echo "🚀 启动 TextLingo2 API"
echo "========================"

# 检查是否在正确的目录
if [ ! -f "app/main.py" ]; then
    echo "❌ 请在 api 目录下运行此脚本"
    exit 1
fi

# 检查 conda 环境
if ! conda env list | grep -q "^${CONDA_ENV_NAME} "; then
    echo "❌ 未找到 ${CONDA_ENV_NAME} 环境"
    echo "请先运行 ./start_dev.sh 创建环境"
    exit 1
fi

# 激活 conda 环境
echo "🔄 激活 ${CONDA_ENV_NAME} 环境..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV_NAME}"

# 设置 PYTHONPATH
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# 加载环境变量
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
else
    echo "❌ 未找到 .env 文件"
    exit 1
fi


# 清理旧进程
echo "🧹 清理旧进程..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true

# 等待进程完全结束
sleep 2

# 创建日志目录
mkdir -p logs

echo "🚀 启动服务..."
echo ""
echo "📚 服务地址:"
echo "  - API 文档: http://localhost:8000/api/v1/docs"
echo "  - 健康检查: http://localhost:8000/health"
echo ""
echo "🛑 停止所有服务: Ctrl+C"
echo "====================================="

# 启动 API 服务
echo "🚀 启动 API 服务..."
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 