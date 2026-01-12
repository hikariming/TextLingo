#!/bin/bash

# TextLingo2 环境配置快速设置脚本

set -e

echo "🔧 TextLingo2 环境配置设置"
echo "=========================="

# 检查是否存在 .env 文件
if [ -f ".env" ]; then
    echo "⚠️  发现已存在的 .env 文件"
    read -p "是否覆盖现有配置？(y/N): " overwrite
    if [[ ! $overwrite =~ ^[Yy]$ ]]; then
        echo "❌ 取消配置，保留现有 .env 文件"
        exit 0
    fi
fi

# 复制示例文件
echo "📋 复制环境变量示例文件..."
cp env.example .env

# 生成安全密钥
echo "🔑 生成安全密钥..."
JWT_SECRET=$(openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)

echo "生成的密钥："
echo "JWT_SECRET_KEY=$JWT_SECRET"
echo "SECRET_KEY=$SECRET_KEY"

# 更新 .env 文件中的密钥
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/your-super-secret-jwt-key-32-characters-long/$JWT_SECRET/g" .env
    sed -i '' "s/your-super-secret-app-key-32-characters-long/$SECRET_KEY/g" .env
else
    # Linux
    sed -i "s/your-super-secret-jwt-key-32-characters-long/$JWT_SECRET/g" .env
    sed -i "s/your-super-secret-app-key-32-characters-long/$SECRET_KEY/g" .env
fi

echo "✅ 安全密钥已自动填入 .env 文件"

echo ""
echo "📝 接下来您需要手动配置以下设置："

echo ""
echo "🗃️  1. Supabase 配置："
echo "   • 访问 https://supabase.com/dashboard"
echo "   • 选择您的项目 (或创建新项目)"
echo "   • 进入 Settings > API"
echo "   • 复制以下值到 .env 文件："
echo "     - Project URL → SUPABASE_URL"
echo "     - anon public key → SUPABASE_ANON_KEY"
echo "     - service_role secret key → SUPABASE_SERVICE_ROLE_KEY"

echo ""
echo "🚀 2. Redis 配置 (推荐免费服务)："
echo "   ⭐ Upstash Redis (最推荐，默认已配置)："
echo "     • 注册: https://console.upstash.com"
echo "     • 创建数据库 > Global > Free"
echo "     • 复制 Redis URL 替换 .env 中的占位符"
echo ""
echo "   🏢 或选择其他免费服务："
echo "     • Redis Cloud: https://redis.com/try-free"
echo "     • Railway: https://railway.app"
echo "     • Render: https://render.com"

echo ""
echo "🎯 快速编辑 .env 文件："
echo "   nano .env"
echo "   或"
echo "   code .env  # 如果使用 VS Code"

echo ""
echo "✨ 配置完成后，运行以下命令启动服务："
echo "   ./start_dev.sh" 