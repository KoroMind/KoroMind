#!/bin/bash
# KoroMind Setup Script
# Automates Docker-first setup on a fresh Debian/Ubuntu VM (GCP, AWS, or any Linux box)
set -e

echo "=== KoroMind Setup ==="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

install_docker() {
    echo -e "${YELLOW}[2/5] Installing Docker Engine + Compose plugin...${NC}"
    sudo apt-get install -y ca-certificates gnupg
    sudo install -m 0755 -d /etc/apt/keyrings

    . /etc/os-release
    DOCKER_DISTRO="ubuntu"
    if [ "${ID}" = "debian" ]; then
        DOCKER_DISTRO="debian"
    fi

    curl -fsSL "https://download.docker.com/linux/${DOCKER_DISTRO}/gpg" | \
        sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${DOCKER_DISTRO} \
      ${VERSION_CODENAME} stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo systemctl enable --now docker
    sudo usermod -aG docker "$USER"

    # Provide legacy `docker-compose` command for compatibility.
    if ! command -v docker-compose >/dev/null 2>&1; then
        sudo tee /usr/local/bin/docker-compose > /dev/null <<'EOF'
#!/bin/sh
exec docker compose "$@"
EOF
        sudo chmod +x /usr/local/bin/docker-compose
    fi
}

install_obsidian() {
    echo -e "${YELLOW}[3/5] Installing Obsidian desktop app...${NC}"

    if command -v obsidian >/dev/null 2>&1; then
        echo "Obsidian CLI already available."
        return
    fi

    ARCH=$(dpkg --print-architecture)
    if [ "$ARCH" != "amd64" ] && [ "$ARCH" != "arm64" ]; then
        echo "Warning: unsupported architecture for Obsidian package ($ARCH). Skipping install."
        return
    fi

    OBSIDIAN_VERSION="1.11.7"
    PKG_PATH="/tmp/obsidian_${OBSIDIAN_VERSION}_${ARCH}.deb"
    PKG_URL="https://github.com/obsidianmd/obsidian-releases/releases/download/v${OBSIDIAN_VERSION}/obsidian_${OBSIDIAN_VERSION}_${ARCH}.deb"

    if curl -fL "$PKG_URL" -o "$PKG_PATH"; then
        if sudo apt-get install -y "$PKG_PATH"; then
            echo "Installed Obsidian ${OBSIDIAN_VERSION} (${ARCH})."
        else
            echo "Warning: failed to install Obsidian package. You can install manually later."
        fi
        rm -f "$PKG_PATH"
    else
        echo "Warning: failed to download Obsidian package. You can install manually later."
    fi
}

# 1. Install system packages
echo -e "${YELLOW}[1/5] Installing system packages...${NC}"
sudo apt-get update
sudo apt-get install -y git curl

install_docker
install_obsidian

# 4. Clone repo if not already in it
echo -e "${YELLOW}[4/5] Setting up repository...${NC}"
if [ ! -f "pyproject.toml" ]; then
    git clone -b local-setup-docs https://github.com/KoroMind/KoroMind.git
    cd KoroMind
fi
REPO_DIR=$(pwd)

# Ensure required submodules are present for Docker build context.
git config submodule.\".claude-settings\".url https://github.com/ToruAI/toru-claude-settings.git || true
git submodule sync --recursive
if ! git submodule update --init --recursive; then
    echo "Warning: failed to fetch .claude-settings submodule; creating local fallback directory."
fi
if [ ! -d ".claude-settings" ] || [ -z "$(ls -A .claude-settings 2>/dev/null)" ]; then
    mkdir -p .claude-settings
    cat > .claude-settings/README.md <<'EOF'
Fallback Claude settings directory created by setup script.
If you have access to the settings submodule, run:
git submodule update --init --recursive
EOF
fi

# 5. Create .env if it doesn't exist
echo -e "${YELLOW}[5/5] Setting up configuration...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
else
    echo ".env already exists, skipping"
fi

mkdir -p "$HOME/claude-work-dir" "$HOME/claude-voice-sandbox"

echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env and add your API keys:"
echo "   nano $REPO_DIR/.env"
echo ""
echo "   Required keys:"
echo "   - ANTHROPIC_API_KEY"
echo "   - ELEVENLABS_API_KEY"
echo "   - TELEGRAM_BOT_TOKEN"
echo "   - TELEGRAM_DEFAULT_CHAT_ID"
echo ""
echo "   Also update these paths (use absolute paths, not ~):"
echo "   - KOROMIND_DATA_DIR"
echo "   - CLAUDE_WORKING_DIR"
echo "   - CLAUDE_SANDBOX_DIR"
echo "2. Start with Docker Compose:"
echo "   cd $REPO_DIR && docker-compose --profile telegram up -d --build"
echo ""
echo "3. Check logs:"
echo "   cd $REPO_DIR && docker-compose logs -f koro"
echo ""
echo "Docker was installed and enabled."
echo "If 'docker' is still denied for your user, reconnect SSH or run: newgrp docker"
echo "Obsidian was installed if a compatible package was available."
echo "In Obsidian: Settings -> General -> Command line interface (enable it)."
echo ""
