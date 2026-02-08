#!/bin/bash

# ============================================
# TextLingo Desktop 一键启动调试脚本
# 功能：Kill占用端口 -> 检查依赖 -> 启动开发服务器
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的信息
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 切换到脚本所在目录（项目根目录）
cd "$(dirname "$0")" || exit 1
info "工作目录: $(pwd)"

# ============================================
# Step 1: Kill占用端口 (1420 - Vite, 1421 - HMR)
# ============================================
echo ""
info "Step 1: 检查并释放占用端口..."

kill_port() {
    local port=$1
    local pid=$(lsof -ti tcp:$port 2>/dev/null)
    
    if [ -n "$pid" ]; then
        warn "端口 $port 被进程 $pid 占用，正在终止..."
        kill -9 $pid 2>/dev/null
        if [ $? -eq 0 ]; then
            success "已终止占用端口 $port 的进程 (PID: $pid)"
        else
            error "无法终止进程 $pid"
        fi
    else
        success "端口 $port 未被占用"
    fi
}

# Kill Vite 开发服务器端口
kill_port 1420

# Kill HMR 端口
kill_port 1421

# 等待端口完全释放
sleep 1

# ============================================
# Step 2: 检查并安装依赖
# ============================================
echo ""
info "Step 2: 检查依赖..."

# 检测包管理器（优先使用 pnpm）
if command -v pnpm &> /dev/null; then
    PKG_MANAGER="pnpm"
elif command -v npm &> /dev/null; then
    PKG_MANAGER="npm"
else
    error "未找到 pnpm 或 npm，请先安装 Node.js 包管理器"
    exit 1
fi

info "使用包管理器: $PKG_MANAGER"

# 检查 node_modules 是否存在
if [ ! -d "node_modules" ]; then
    warn "未找到 node_modules，正在安装依赖..."
    $PKG_MANAGER install
    if [ $? -ne 0 ]; then
        error "依赖安装失败"
        exit 1
    fi
    success "依赖安装完成"
else
    # 检查 package.json 是否比 node_modules 更新
    if [ "package.json" -nt "node_modules" ]; then
        warn "package.json 已更新，正在同步依赖..."
        $PKG_MANAGER install
        if [ $? -ne 0 ]; then
            error "依赖同步失败"
            exit 1
        fi
        success "依赖同步完成"
    else
        success "依赖已是最新"
    fi
fi

# ============================================
# Step 3: 启动 Tauri 开发服务器
# ============================================
echo ""
info "Step 3: 启动 Tauri 开发服务器..."
success "============================================"
success "  TextLingo Desktop 开发环境启动中..."
success "  Vite Server: http://localhost:1420"
success "  按 Ctrl+C 停止服务器"
success "============================================"
echo ""

# 启动 Tauri 开发服务器
if [ "$PKG_MANAGER" = "pnpm" ]; then
    pnpm tauri dev
else
    npm run tauri dev
fi
