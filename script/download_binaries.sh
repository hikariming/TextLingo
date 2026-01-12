#!/bin/bash

# Define the target directory
TARGET_DIR="textlingo-desktop/src-tauri/binaries"

# Create the directory if it doesn't exist
mkdir -p "$TARGET_DIR"

echo "Downloading binaries to $TARGET_DIR..."

# --- yt-dlp ---
# Define versions/URLs for yt-dlp
YT_DLP_BASE="https://github.com/yt-dlp/yt-dlp/releases/latest/download"

echo "Downloading yt-dlp binaries..."
curl -L -o "$TARGET_DIR/yt-dlp-x86_64-apple-darwin" "$YT_DLP_BASE/yt-dlp_macos"
curl -L -o "$TARGET_DIR/yt-dlp-aarch64-apple-darwin" "$YT_DLP_BASE/yt-dlp_macos"
curl -L -o "$TARGET_DIR/yt-dlp-x86_64-unknown-linux-gnu" "$YT_DLP_BASE/yt-dlp"
curl -L -o "$TARGET_DIR/yt-dlp-x86_64-pc-windows-msvc.exe" "$YT_DLP_BASE/yt-dlp.exe"

# --- ffmpeg ---
# Downloading standalone binaries for FFmpeg is more complex due to variations.
# We will use reliable sources for static builds.

echo "Downloading FFmpeg binaries (this may take a while)..."

# macOS (Intel & Apple Silicon) - using evermeet.cx
# Note: These are zip files, we need to extract them.
echo "Downloading FFmpeg for macOS..."
curl -L -o ffmpeg_mac.zip "https://evermeet.cx/ffmpeg/ffmpeg-6.1.1.zip"
unzip -o ffmpeg_mac.zip ffmpeg
mv ffmpeg "$TARGET_DIR/ffmpeg-x86_64-apple-darwin"
cp "$TARGET_DIR/ffmpeg-x86_64-apple-darwin" "$TARGET_DIR/ffmpeg-aarch64-apple-darwin" # Assuming universal or Rosetta fallback for simplicity if specific arm64 build isn't handy in single file. 
# Actually evermeet is x86_64. For arm64 native, strict users might want separate, but x86_64 works on M1 via Rosetta. 
# Leaving as x86_64 for both for now to ensure functionality.
rm ffmpeg_mac.zip

# Linux
echo "Downloading FFmpeg for Linux..."
curl -L -o ffmpeg_linux.tar.xz "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
tar -xf ffmpeg_linux.tar.xz --wildcards '*/ffmpeg' --strip-components=1
mv ffmpeg "$TARGET_DIR/ffmpeg-x86_64-unknown-linux-gnu"
rm ffmpeg_linux.tar.xz

# Windows
echo "Downloading FFmpeg for Windows..."
# Using gyan.dev essentials
curl -L -o ffmpeg_win.zip "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
unzip -o -j ffmpeg_win.zip "*/bin/ffmpeg.exe"
mv ffmpeg.exe "$TARGET_DIR/ffmpeg-x86_64-pc-windows-msvc.exe"
rm ffmpeg_win.zip

# Make executable
chmod +x "$TARGET_DIR"/*

echo "All binaries downloaded and configured successfully to $TARGET_DIR"
