#!/bin/bash

# 根据当前平台下载所需的 FFmpeg 和 yt-dlp 二进制文件
# 此脚本支持 macOS、Linux 和 Windows (Git Bash/MSYS2)

# 定义目标目录
TARGET_DIR="textlingo-desktop/src-tauri/binaries"

# 创建目录
mkdir -p "$TARGET_DIR"

echo "Downloading binaries to $TARGET_DIR..."

# 检测当前操作系统
OS_TYPE="$(uname -s)"
ARCH_TYPE="$(uname -m)"

echo "Detected OS: $OS_TYPE, Architecture: $ARCH_TYPE"

# --- yt-dlp ---
YT_DLP_BASE="https://github.com/yt-dlp/yt-dlp/releases/latest/download"

echo "Downloading yt-dlp binaries..."
case "$OS_TYPE" in
    Darwin)
        curl -L --fail -o "$TARGET_DIR/yt-dlp-x86_64-apple-darwin" "$YT_DLP_BASE/yt-dlp_macos" || echo "Warning: Failed x86_64"
        curl -L --fail -o "$TARGET_DIR/yt-dlp-aarch64-apple-darwin" "$YT_DLP_BASE/yt-dlp_macos" || echo "Warning: Failed aarch64"
        ;;
    Linux)
        curl -L --fail -o "$TARGET_DIR/yt-dlp-x86_64-unknown-linux-gnu" "$YT_DLP_BASE/yt-dlp" || echo "Warning: Failed linux"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        curl -L --fail -o "$TARGET_DIR/yt-dlp-x86_64-pc-windows-msvc.exe" "$YT_DLP_BASE/yt-dlp.exe" || echo "Warning: Failed windows"
        ;;
esac

# --- ffmpeg ---
echo "Downloading FFmpeg binaries (this may take a while)..."

download_ffmpeg_mac() {
    local success=0
    
    # 方法 1: BtbN static builds (GitHub releases)
    echo "Trying BtbN FFmpeg builds..."
    if curl -L --fail --max-time 120 -o "$TARGET_DIR/ffmpeg-x86_64-apple-darwin" \
        "https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0/ffmpeg-darwin-x64" 2>/dev/null; then
        success=1
    fi
    
    # 方法 2: evermeet.cx (如果方法 1 失败)
    if [ $success -eq 0 ]; then
        echo "Trying evermeet.cx..."
        if curl -L --fail --max-time 120 -o ffmpeg_mac.zip "https://evermeet.cx/ffmpeg/getrelease/zip" 2>/dev/null; then
            unzip -o ffmpeg_mac.zip -d ffmpeg_extract 2>/dev/null || unzip -o ffmpeg_mac.zip 2>/dev/null
            if [ -f "ffmpeg_extract/ffmpeg" ]; then
                mv ffmpeg_extract/ffmpeg "$TARGET_DIR/ffmpeg-x86_64-apple-darwin"
                rm -rf ffmpeg_extract
                success=1
            elif [ -f "ffmpeg" ]; then
                mv ffmpeg "$TARGET_DIR/ffmpeg-x86_64-apple-darwin"
                success=1
            fi
            rm -f ffmpeg_mac.zip
        fi
    fi
    
    # 复制到 aarch64 (通过 Rosetta 2 运行 x86_64 二进制文件)
    if [ $success -eq 1 ] && [ -f "$TARGET_DIR/ffmpeg-x86_64-apple-darwin" ]; then
        cp "$TARGET_DIR/ffmpeg-x86_64-apple-darwin" "$TARGET_DIR/ffmpeg-aarch64-apple-darwin"
        chmod +x "$TARGET_DIR/ffmpeg-x86_64-apple-darwin" "$TARGET_DIR/ffmpeg-aarch64-apple-darwin"
        echo "FFmpeg for macOS downloaded successfully!"
        return 0
    fi
    
    echo "Error: Failed to download FFmpeg for macOS"
    return 1
}

download_ffmpeg_linux() {
    echo "Downloading FFmpeg for Linux..."
    
    if curl -L --fail --max-time 180 -o ffmpeg_linux.tar.xz \
        "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz" 2>/dev/null; then
        tar -xf ffmpeg_linux.tar.xz --wildcards '*/ffmpeg' --strip-components=1 2>/dev/null || \
            tar -xf ffmpeg_linux.tar.xz 2>/dev/null
        
        # 找到 ffmpeg 可执行文件
        if [ -f "ffmpeg" ]; then
            mv ffmpeg "$TARGET_DIR/ffmpeg-x86_64-unknown-linux-gnu"
        else
            find . -name "ffmpeg" -type f -executable -exec mv {} "$TARGET_DIR/ffmpeg-x86_64-unknown-linux-gnu" \; 2>/dev/null
        fi
        
        rm -f ffmpeg_linux.tar.xz
        rm -rf ffmpeg-*-static 2>/dev/null
        
        if [ -f "$TARGET_DIR/ffmpeg-x86_64-unknown-linux-gnu" ]; then
            chmod +x "$TARGET_DIR/ffmpeg-x86_64-unknown-linux-gnu"
            echo "FFmpeg for Linux downloaded successfully!"
            return 0
        fi
    fi
    
    echo "Error: Failed to download FFmpeg for Linux"
    return 1
}

download_ffmpeg_windows() {
    echo "Downloading FFmpeg for Windows..."
    
    # 使用 gyan.dev 的 essentials 版本
    if curl -L --fail --max-time 180 -o ffmpeg_win.zip \
        "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" 2>/dev/null; then
        unzip -o -j ffmpeg_win.zip "*/bin/ffmpeg.exe" 2>/dev/null
        if [ -f "ffmpeg.exe" ]; then
            mv ffmpeg.exe "$TARGET_DIR/ffmpeg-x86_64-pc-windows-msvc.exe"
            rm -f ffmpeg_win.zip
            echo "FFmpeg for Windows downloaded successfully!"
            return 0
        fi
        rm -f ffmpeg_win.zip
    fi
    
    # 备用: BtbN builds
    echo "Trying BtbN builds for Windows..."
    if curl -L --fail --max-time 180 -o ffmpeg_win.zip \
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip" 2>/dev/null; then
        unzip -o -j ffmpeg_win.zip "*/bin/ffmpeg.exe" 2>/dev/null
        if [ -f "ffmpeg.exe" ]; then
            mv ffmpeg.exe "$TARGET_DIR/ffmpeg-x86_64-pc-windows-msvc.exe"
            rm -f ffmpeg_win.zip
            echo "FFmpeg for Windows downloaded successfully!"
            return 0
        fi
        rm -f ffmpeg_win.zip
    fi
    
    echo "Error: Failed to download FFmpeg for Windows"
    return 1
}

# 根据平台执行下载
case "$OS_TYPE" in
    Darwin)
        download_ffmpeg_mac
        ;;
    Linux)
        download_ffmpeg_linux
        ;;
    MINGW*|MSYS*|CYGWIN*)
        download_ffmpeg_windows
        ;;
    *)
        echo "Unknown OS: $OS_TYPE"
        exit 1
        ;;
esac

# 列出下载的文件
echo ""
echo "Downloaded files:"
ls -la "$TARGET_DIR/"

echo ""
echo "Download script completed!"
