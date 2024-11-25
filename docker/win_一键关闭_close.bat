@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 设置颜色代码
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "NC=[0m"

echo %YELLOW%开始关闭服务... / Starting to shut down services...%NC%

:: 检查 Docker 是否在运行
docker info >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo %RED%Docker 未运行，无需关闭服务 / Docker is not running, no services to stop%NC%
    pause
    exit /b 0
)

:: 检查是否有正在运行的容器
docker-compose ps -q >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo %YELLOW%没有检测到正在运行的服务 / No running services detected%NC%
    pause
    exit /b 0
)

echo %YELLOW%正在停止并移除所有容器... / Stopping and removing all containers...%NC%

docker-compose down
if %ERRORLEVEL% EQU 0 (
    echo %GREEN%所有服务已成功关闭！/ All services have been successfully stopped!%NC%
) else (
    echo %RED%关闭服务时发生错误 / Error occurred while stopping services%NC%
)

echo %GREEN%操作完成 / Operation completed%NC%
pause