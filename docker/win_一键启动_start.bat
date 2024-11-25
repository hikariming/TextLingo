@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo Starting environment check...

:: Check if Docker is installed
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Docker not found! Please install Docker first
    echo Windows installation:
    echo 1. Visit: https://www.docker.com/products/docker-desktop
    echo 2. Download and install Docker Desktop
    pause
    exit /b 1
)

:: Check if Docker is running
docker info >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Docker is not running! Please start Docker Desktop
    echo How to start:
    echo 1. Open Docker Desktop application
    echo 2. Wait for Docker engine to start
    echo 3. Run this script again
    pause
    exit /b 1
)

echo Docker is running properly

goto main

:: Check image function
:check_and_load_image
setlocal
set "image_name=%~1"
set "tar_file=%~2"

if "%image_name%"=="" (
    echo Error: Image name not provided
    exit /b 1
)

echo Checking image: %image_name%

:: Check if image exists
docker images | findstr /i "%image_name%" >nul
if %ERRORLEVEL% EQU 0 (
    echo Image exists: %image_name%
    exit /b 0
)

if exist "%tar_file%" (
    echo Loading image from local file: %tar_file%
    docker load -i "%tar_file%"
    if %ERRORLEVEL% EQU 0 (
        echo Successfully loaded image: %image_name%
        exit /b 0
    )
)

echo Pulling image from Docker Hub: %image_name%
echo Note: If you're in mainland China, you may need a VPN or Docker registry mirror

docker pull %image_name%
if %ERRORLEVEL% EQU 0 (
    echo Successfully pulled image: %image_name%
    exit /b 0
) else (
    echo Error: Failed to pull image: %image_name%
    exit /b 1
)
endlocal

:main
echo Starting to check required images...

:: Check required images
call :check_and_load_image "rqlove/textlingo-api:v0.22" "textlingo-api.tar"
if %ERRORLEVEL% NEQ 0 goto error
call :check_and_load_image "rqlove/textlingo-web:v0.22" "textlingo-web.tar"
if %ERRORLEVEL% NEQ 0 goto error
call :check_and_load_image "mongo:7.0.14" "mongo.tar"
if %ERRORLEVEL% NEQ 0 goto error

echo Starting services...
docker-compose up -d
if %ERRORLEVEL% EQU 0 (
    echo All services started successfully!
    echo Service access URLs:
    echo API Service: http://localhost:3001
    echo Web Service: http://localhost:3000
    echo MongoDB: localhost:27017
    goto end
)

:error
echo Error occurred while processing images
pause
exit /b 1

:end
pause