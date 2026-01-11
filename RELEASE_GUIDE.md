# TextLingo Desktop Release Guide

This guide describes how to package and release the TextLingo Desktop application.

## 0.1.0 Packaging

The version 0.1.0 configuration is already set up.

## How to Build and Release

We use **GitHub Actions** to automatically build the application for macOS, Windows, and Linux.

### 1. Tag a Release
The build workflow is triggered when you push a tag starting with `v`.

```bash
git tag v0.1.0
git push origin v0.1.0
```

### 2. Monitor Build
Go to the "Actions" tab in your GitHub repository to see the build progress.
There will be a "publish" workflow running.

### 3. Download Assets
Once the build is complete, a new **Draft Release** will be created in the "Releases" section of your repository.
It will contain:
- **macOS**: `.dmg`, `.app.tar.gz` (Universal/Intel/Apple Silicon depending on config)
- **Windows**: `.msi`, `.exe`
- **Linux**: `.AppImage`, `.deb`

## Local Build (macOS)
To build the macOS version locally for testing:

```bash
cd textlingo-desktop
npm run tauri build
```
The output will be in `src-tauri/target/release/bundle/dmg`.
