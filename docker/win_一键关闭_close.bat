@echo off
chcp 65001 >nul

echo Stopping Docker services...
docker-compose down

echo Checking for remaining MongoDB containers...
for /f "tokens=*" %%i in ('docker ps -q --filter "ancestor=mongo:latest" --filter "ancestor=mongo:7.0.14"') do (
    echo Stopping MongoDB container: %%i
    docker stop %%i
)

echo Cleanup completed.
pause