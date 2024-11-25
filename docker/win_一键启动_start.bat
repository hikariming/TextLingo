@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 设置颜色代码
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "NC=[0m"

echo %GREEN%开始检查环境... / Starting environment check...%NC%

:: 检查 Docker 是否已安装
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo %RED%未检测到 Docker！请先安装 Docker%NC%
    echo %RED%Docker not found! Please install Docker first%NC%
    echo %YELLOW%Windows 安装方法 / Windows installation:%NC%
    echo 1. 访问 / Visit: https://www.docker.com/products/docker-desktop
    echo 2. 下载并安装 Docker Desktop / Download and install Docker Desktop
    pause
    exit /b 1
)

:: 检查 Docker 是否在运行
docker info >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo %RED%Docker 未运行！请启动 Docker Desktop%NC%
    echo %RED%Docker is not running! Please start Docker Desktop%NC%
    echo %YELLOW%如何启动 / How to start:%NC%
    echo 1. 打开 Docker Desktop 应用 / Open Docker Desktop application
    echo 2. 等待 Docker 引擎启动 / Wait for Docker engine to start
    echo 3. 再次运行此脚本 / Run this script again
    pause
    exit /b 1
)

echo %GREEN%Docker 运行正常 / Docker is running properly%NC%

:: 检查镜像函数
:check_and_load_image
set "image_name=%~1"
set "tar_file=%~2"

echo 检查镜像 / Checking image: %YELLOW%%image_name%%NC%

docker images | findstr "%image_name%" >nul
if %ERRORLEVEL% EQU 0 (
    echo %GREEN%镜像已存在 / Image exists: %image_name%%NC%
    goto :eof
)

if exist "%tar_file%" (
    echo 正在从本地文件加载镜像 / Loading image from local file: %YELLOW%%tar_file%%NC%
    docker load -i "%tar_file%"
    if %ERRORLEVEL% EQU 0 (
        echo %GREEN%成功加载镜像 / Successfully loaded image: %image_name%%NC%
        goto :eof
    )
)

echo 正在从Docker Hub拉取镜像 / Pulling image from Docker Hub: %YELLOW%%image_name%%NC%
echo %RED%注意：如果您在中国内地，可能需要使用科学上网或配置镜像加速器%NC%
echo %RED%Note: If you're in mainland China, you may need a VPN or Docker registry mirror%NC%

docker pull "%image_name%"
if %ERRORLEVEL% EQU 0 (
    echo %GREEN%成功拉取镜像 / Successfully pulled image: %image_name%%NC%
) else (
    echo %RED%错误：无法拉取镜像 / Error: Failed to pull image: %image_name%%NC%
    pause
    exit /b 1
)
goto :eof

echo %YELLOW%开始检查必需的镜像 / Starting to check required images...%NC%

:: 检查所需的镜像
call :check_and_load_image "rqlove/textlingo-api:v0.20" "textlingo-api.tar"
call :check_and_load_image "rqlove/textlingo-web:v0.20" "textlingo-web.tar"
call :check_and_load_image "mongo:latest" "mongo.tar"

echo %YELLOW%正在启动服务 / Starting services...%NC%
docker-compose up -d
if %ERRORLEVEL% EQU 0 (
    echo %GREEN%所有服务已成功启动！/ All services started successfully!%NC%
    echo %GREEN%服务访问地址 / Service access URLs:%NC%
    echo API 服务 / API Service: %YELLOW%http://localhost:3001%NC%
    echo Web 服务 / Web Service: %YELLOW%http://localhost:3000%NC%
    echo MongoDB: %YELLOW%localhost:27017%NC%
) else (
    echo %RED%启动服务时发生错误 / Error occurred while starting services%NC%
    pause
    exit /b 1
)

pause