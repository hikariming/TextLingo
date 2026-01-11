#!/bin/bash

# 获取脚本所在目录的绝对路径
cd "$(dirname "$0")"

# 设置颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}开始关闭服务... / Starting to shut down services...${NC}"

# 检查 Docker 是否在运行
if ! docker info &> /dev/null; then
    echo -e "${RED}Docker 未运行，无需关闭服务 / Docker is not running, no services to stop${NC}"
    read -p "按回车键退出... / Press Enter to exit..."
    exit 0
fi

# 检查是否有正在运行的容器
if ! docker-compose ps -q 2>/dev/null | grep -q .; then
    echo -e "${YELLOW}没有检测到正在运行的服务 / No running services detected${NC}"
    read -p "按回车键退出... / Press Enter to exit..."
    exit 0
fi

echo -e "${YELLOW}正在停止并移除所有容器... / Stopping and removing all containers...${NC}"

if docker-compose down; then
    echo -e "${GREEN}所有服务已成功关闭！/ All services have been successfully stopped!${NC}"
else
    echo -e "${RED}关闭服务时发生错误 / Error occurred while stopping services${NC}"
fi

echo -e "${GREEN}操作完成 / Operation completed${NC}"
read -p "按回车键退出... / Press Enter to exit..."