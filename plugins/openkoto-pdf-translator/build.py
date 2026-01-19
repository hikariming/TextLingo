#!/usr/bin/env python3
"""
PyInstaller build script for OpenKoto PDF Translator plugin.
Builds standalone executables for distribution.
"""

import PyInstaller.__main__
import platform
import sys
from pathlib import Path

def get_platform_name():
    """Get platform name for output filename."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "darwin":
        if machine == "arm64":
            return "macos-arm64"
        return "macos-x64"
    elif system == "windows":
        return "win-x64"
    elif system == "linux":
        return "linux-x64"
    return f"{system}-{machine}"


def build():
    """Build the executable."""
    platform_name = get_platform_name()
    output_name = f"openkoto-pdf-translator-{platform_name}"
    
    # Get the directory of this script
    script_dir = Path(__file__).parent.absolute()
    main_script = script_dir / "openkoto_pdf_translator" / "pdf2zh.py"
    
    # PyInstaller options
    args = [
        str(main_script),
        "--onefile",
        "--name", output_name,
        "--clean",
        # Hidden imports for dynamic dependencies
        "--hidden-import", "openai",
        "--hidden-import", "requests",
        "--hidden-import", "numpy",
        "--hidden-import", "cv2",
        "--hidden-import", "onnxruntime",
        "--hidden-import", "PIL",
        "--hidden-import", "tqdm",
        "--hidden-import", "peewee",
        "--hidden-import", "fontTools",
        "--hidden-import", "pikepdf",
        "--hidden-import", "pdfminer",
        "--hidden-import", "pymupdf",
        "--hidden-import", "rich",
        "--hidden-import", "tenacity",
        "--hidden-import", "huggingface_hub",
        # Exclude unnecessary modules to reduce size
        "--exclude-module", "gradio",
        "--exclude-module", "gradio_pdf",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        # Output directory
        "--distpath", str(script_dir / "dist"),
        "--workpath", str(script_dir / "build"),
        "--specpath", str(script_dir / "build"),
    ]
    
    # Add icon on Windows/macOS if available
    icon_path = script_dir / "assets" / "icon.ico"
    if icon_path.exists():
        args.extend(["--icon", str(icon_path)])
    
    print(f"Building {output_name}...")
    print(f"Platform: {platform_name}")
    print(f"Main script: {main_script}")
    
    PyInstaller.__main__.run(args)
    
    print(f"\n✅ Build complete! Executable: dist/{output_name}")
    

if __name__ == "__main__":
    build()
