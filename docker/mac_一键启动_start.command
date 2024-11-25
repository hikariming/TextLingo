#!/bin/bash

# 获取脚本所在目录的绝对路径
cd "$(dirname "$0")"

# 设置颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始检查环境... / Starting environment check...${NC}"

# 检查 Docker 是否已安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}未检测到 Docker！请先安装 Docker${NC}"
    echo -e "${RED}Docker not found! Please install Docker first${NC}"
    echo -e "${YELLOW}MacOS 安装方法 / MacOS installation:${NC}"
    echo "1. 访问 / Visit: https://www.docker.com/products/docker-desktop"
    echo "2. 下载并安装 Docker Desktop / Download and install Docker Desktop"
    exit 1
fi

# 检查 Docker 是否在运行
if ! docker info &> /dev/null; then
    echo -e "${RED}Docker 未运行！请启动 Docker Desktop${NC}"
    echo -e "${RED}Docker is not running! Please start Docker Desktop${NC}"
    echo -e "${YELLOW}如何启动 / How to start:${NC}"
    echo "1. 打开 Docker Desktop 应用 / Open Docker Desktop application"
    echo "2. 等待 Docker 引擎启动 / Wait for Docker engine to start"
    echo "3. 再次运行此脚本 / Run this script again"
    exit 1
fi

echo -e "${GREEN}Docker 运行正常 / Docker is running properly${NC}"

# 检查所需的镜像
check_and_load_image() {
    local image_name=$1
    local tar_file=$2
    
    echo -e "检查镜像 / Checking image: ${YELLOW}$image_name${NC}"
    
    if docker images | grep -q "$image_name"; then
        echo -e "${GREEN}镜像已存在 / Image exists: $image_name${NC}"
        return 0
    fi
    
    # 尝试从本地tar文件加载
    if [ -f "$tar_file" ]; then
        echo -e "正在从本地文件加载镜像 / Loading image from local file: ${YELLOW}$tar_file${NC}"
        docker load -i "$tar_file"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}成功加载镜像 / Successfully loaded image: $image_name${NC}"
            return 0
        fi
    fi
    
    # 从Docker Hub拉取
    echo -e "正在从Docker Hub拉取镜像 / Pulling image from Docker Hub: ${YELLOW}$image_name${NC}"
    echo -e "${RED}注意：如果您在中国内地，可能需要使用科学上网或配置镜像加速器${NC}"
    echo -e "${RED}Note: If you're in mainland China, you may need a VPN or Docker registry mirror${NC}"
    
    if docker pull "$image_name"; then
        echo -e "${GREEN}成功拉取镜像 / Successfully pulled image: $image_name${NC}"
        return 0
    else
        echo -e "${RED}错误：无法拉取镜像 / Error: Failed to pull image: $image_name${NC}"
        return 1
    fi
}

echo -e "${YELLOW}开始检查必需的镜像 / Starting to check required images...${NC}"

# 检查所需的镜像
check_and_load_image "rqlove/textlingo-api:v0.22" "textlingo-api.tar" || exit 1
check_and_load_image "rqlove/textlingo-web:v0.22" "textlingo-web.tar" || exit 1
check_and_load_image "mongo:latest" "mongo.tar" || exit 1

echo -e "${YELLOW}正在启动服务 / Starting services...${NC}"
if docker-compose up -d; then
    echo -e "${GREEN}所有服务已成功启动！/ All services started successfully!${NC}"
    echo -e "${GREEN}服务访问地址 / Service access URLs:${NC}"
    echo -e "API 服务 / API Service: ${YELLOW}http://localhost:3001${NC}"
    echo -e "Web 服务 / Web Service: ${YELLOW}http://localhost:3000${NC}"
    echo -e "MongoDB: ${YELLOW}localhost:27017${NC}"
else
    echo -e "${RED}启动服务时发生错误 / Error occurred while starting services${NC}"
    exit 1
fi