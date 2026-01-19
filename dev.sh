#!/bin/bash

# OpenKoto Development Startup Script
# Handles environment setup (uv, python, rust) and starts the app with menu options

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper for handling uv installation
check_uv() {
    # Try sourcing common paths first
    if [ -f "$HOME/.cargo/env" ]; then source "$HOME/.cargo/env"; fi
    if [ -d "$HOME/.local/bin" ]; then export PATH="$HOME/.local/bin:$PATH"; fi

    if ! command -v uv &> /dev/null; then
        echo -e "${YELLOW}⚠️  'uv' tool not found.${NC}"
        echo "uv is required for managing Python dependencies efficiently."
        read -p "Install uv now? (y/N) " install_uv
        if [[ $install_uv =~ ^[Yy]$ ]]; then
            curl -LsSf https://astral.sh/uv/install.sh | sh
            # Source new env
            if [ -f "$HOME/.cargo/env" ]; then source "$HOME/.cargo/env"; fi
            export PATH="$HOME/.local/bin:$PATH"
        else
            echo -e "${RED}uv is required for plugin setup. Aborting.${NC}"
            exit 1
        fi
    fi
}

# Helper for Rust check
check_rust() {
    if ! command -v cargo &> /dev/null; then
        echo -e "${YELLOW}⚠️  Rust/Cargo not found.${NC}"
        read -p "Install Rust now? (y/N) " install_rust
        if [[ $install_rust =~ ^[Yy]$ ]]; then
            curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
            source "$HOME/.cargo/env"
        else
            echo -e "${RED}Rust is required. Aborting.${NC}"
            exit 1
        fi
    fi
}

# Helper for Python/Plugin setup
setup_plugins() {
    echo -e "${GREEN}🔧 Setting up Plugin Environment...${NC}"
    check_uv
    
    # 1. Install managed Python 3.10
    echo -e "${GREEN}🐍 Ensuring Python 3.10 is available...${NC}"
    uv python install 3.10
    
    # 2. Check/Create Virtual Environment
    RECREATE_VENV=false
    if [ -d ".venv" ]; then
        # Check if existing venv is suitable
        current_version=$(.venv/bin/python --version 2>&1 | awk '{print $2}')
        # Simple check: start with "3.10", "3.11", or "3.12"
        if [[ ! "$current_version" =~ ^3\.(10|11|12) ]]; then
            echo -e "${YELLOW}⚠️  Existing venv is Python $current_version. Removing to use Python 3.10...${NC}"
            rm -rf .venv
            RECREATE_VENV=true
        fi
    else
        RECREATE_VENV=true
    fi
    
    if [ "$RECREATE_VENV" = true ]; then
        echo -e "${GREEN}📦 Creating virtual environment (Python 3.10)...${NC}"
        uv venv --python 3.10
    fi
    
    source .venv/bin/activate
    
    echo -e "${GREEN}✅ Using Python: $(python --version)${NC}"
    
    PLUGIN_DIR="plugins/openkoto-pdf-translator"
    if [ -d "$PLUGIN_DIR" ]; then
        echo -e "${GREEN}🔌 Installing PDF Translator plugin (with extras)...${NC}"
        uv pip install -e "$PLUGIN_DIR[extra-translators]"
    else
        echo -e "${RED}❌ Plugin directory missing: $PLUGIN_DIR${NC}"
    fi
}

# Helper for npm install
setup_core() {
    echo -e "${GREEN}📦 Installing Core Dependencies...${NC}"
    if [ -d "textlingo-desktop" ]; then
        cd textlingo-desktop && npm install && cd ..
    else
        npm install
    fi
}

# Main Menu
clear
echo -e "${GREEN}🚀 OpenKoto Development Launcher${NC}"
echo "----------------------------------------"
echo "1. Full Setup & Start (Install Plugins + Core Deps + Start)"
echo "2. Quick Start Full (Skip checks, assume env ready)"
echo "3. Core Install & Start (Install Core Deps only + Start)"
echo "4. Quick Start Core (Start only, no python plugins)"
echo "----------------------------------------"
read -p "Select option [1-4]: " choice

case $choice in
    1)
        check_rust
        setup_plugins
        setup_core
        echo -e "${GREEN}✨ Starting Full App...${NC}"
        # Start app
        export PATH="$PWD/.venv/bin:$PATH" # Ensure venv python is first in path for correct plugin loading
        cd textlingo-desktop && npm run tauri dev
        ;;
    2)
        # Quick Full - try to activate venv if exists
        if [ -f ".venv/bin/activate" ]; then
            source .venv/bin/activate
            echo -e "${GREEN}✅ Venv activated.${NC}"
        else
            echo -e "${YELLOW}⚠️  Venv not found, attempting setup...${NC}"
            setup_plugins
        fi
        echo -e "${GREEN}🚀 Quick Starting Full App...${NC}"
        cd textlingo-desktop && npm run tauri dev
        ;;
    3)
        check_rust
        setup_core
        echo -e "${GREEN}✨ Starting Core App...${NC}"
        cd textlingo-desktop && npm run tauri dev
        ;;
    4)
        echo -e "${GREEN}🚀 Quick Starting Core App...${NC}"
        cd textlingo-desktop && npm run tauri dev
        ;;
    *)
        echo -e "${RED}Invalid option selected.${NC}"
        exit 1
        ;;
esac
