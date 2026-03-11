#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Negotium — Local Install Script
#
# Sets up Python 3.13.6 (via pyenv), creates a .venv, installs pip
# packages, and installs Chromium for headless Selenium scraping.
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

PYTHON_VERSION="3.13.6"
VENV_DIR=".venv"

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
fail()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ── 1. System dependencies (Chromium + build deps for pyenv) ─────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo " Negotium — Install Script"
echo "═══════════════════════════════════════════════════════════"
echo ""

install_chromium() {
    info "Installing Chromium and system dependencies..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq \
            chromium-browser \
            chromium-chromedriver \
            2>/dev/null || \
        sudo apt-get install -y -qq \
            chromium \
            chromium-driver \
            2>/dev/null || \
        warn "Could not install chromium via apt. Trying snap..."
        if command -v snap &>/dev/null; then
            sudo snap install chromium
        fi
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y chromium chromium-headless chromedriver
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm chromium
    elif command -v brew &>/dev/null; then
        brew install --cask chromium
    else
        fail "Unsupported package manager. Install Chromium manually."
    fi
}

# Check if Chromium/Chrome is already installed
if command -v google-chrome &>/dev/null; then
    info "Google Chrome found: $(google-chrome --version)"
elif command -v chromium-browser &>/dev/null; then
    info "Chromium found: $(chromium-browser --version)"
elif command -v chromium &>/dev/null; then
    info "Chromium found: $(chromium --version)"
else
    install_chromium
fi

# Verify it installed
if command -v google-chrome &>/dev/null || \
   command -v chromium-browser &>/dev/null || \
   command -v chromium &>/dev/null; then
    info "Browser ready."
else
    fail "Chromium installation failed. Please install it manually."
fi

# ── 2. pyenv + Python ────────────────────────────────────────────────
install_pyenv_build_deps() {
    info "Installing pyenv build dependencies..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get install -y -qq \
            make build-essential libssl-dev zlib1g-dev \
            libbz2-dev libreadline-dev libsqlite3-dev wget curl \
            llvm libncursesw5-dev xz-utils tk-dev \
            libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
    elif command -v dnf &>/dev/null; then
        sudo dnf groupinstall -y "Development Tools"
        sudo dnf install -y zlib-devel bzip2-devel readline-devel \
            sqlite-devel openssl-devel libffi-devel xz-devel
    fi
}

if ! command -v pyenv &>/dev/null; then
    warn "pyenv not found. Installing pyenv..."
    curl -fsSL https://pyenv.run | bash

    # Add to shell config if not already there
    SHELL_RC="$HOME/.bashrc"
    if [[ -f "$HOME/.zshrc" ]] && [[ "$SHELL" == *zsh* ]]; then
        SHELL_RC="$HOME/.zshrc"
    fi

    if ! grep -q 'pyenv' "$SHELL_RC" 2>/dev/null; then
        {
            echo ''
            echo '# pyenv'
            echo 'export PYENV_ROOT="$HOME/.pyenv"'
            echo 'export PATH="$PYENV_ROOT/bin:$PATH"'
            echo 'eval "$(pyenv init -)"'
        } >> "$SHELL_RC"
    fi

    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
    info "pyenv installed."
else
    info "pyenv found."
fi

# Install the target Python version if missing
if ! pyenv versions --bare | grep -qx "$PYTHON_VERSION"; then
    install_pyenv_build_deps
    info "Installing Python $PYTHON_VERSION (this may take a few minutes)..."
    pyenv install "$PYTHON_VERSION"
else
    info "Python $PYTHON_VERSION already installed."
fi

# Set local version for this project
pyenv local "$PYTHON_VERSION"
info "Python version set to $PYTHON_VERSION for this project."

# Unset PYENV_VERSION if it overrides pyenv local
unset PYENV_VERSION 2>/dev/null || true

# Make sure we're using the right python
PYTHON="$(pyenv which python)"
info "Using: $PYTHON ($($PYTHON --version))"

# ── 3. Virtual environment ───────────────────────────────────────────
if [[ -d "$VENV_DIR" ]]; then
    warn "Existing $VENV_DIR found. Recreating..."
    rm -rf "$VENV_DIR"
fi

info "Creating virtual environment in $VENV_DIR..."
"$PYTHON" -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
info "Virtual environment activated."

# ── 4. Python packages ──────────────────────────────────────────────
info "Upgrading pip..."
pip install --upgrade pip --quiet

info "Installing dependencies from requirements.txt..."
pip install -r requirements.txt --quiet

info "All Python packages installed."

# ── 5. Verify ────────────────────────────────────────────────────────
echo ""
echo "─────────────────────────────────────────────────────────"
info "Setup complete!"
echo ""
echo "  Python:    $(python --version)"
echo "  Venv:      $VENV_DIR"
echo "  Packages:  $(pip list --format=columns 2>/dev/null | wc -l) installed"

if command -v google-chrome &>/dev/null; then
    echo "  Browser:   $(google-chrome --version)"
elif command -v chromium-browser &>/dev/null; then
    echo "  Browser:   $(chromium-browser --version 2>/dev/null || echo 'chromium-browser')"
elif command -v chromium &>/dev/null; then
    echo "  Browser:   $(chromium --version 2>/dev/null || echo 'chromium')"
fi

echo ""
echo "  To activate the environment:"
echo "    source $VENV_DIR/bin/activate"
echo ""
echo "  To run Negotium:"
echo "    python main.py"
echo "─────────────────────────────────────────────────────────"
