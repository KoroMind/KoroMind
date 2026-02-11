#!/bin/bash
# KoroMind Setup Script
# Automates setup on a fresh Debian/Ubuntu VM (GCP, AWS, or any Linux box)
set -e

INSTALL_DOCKER=0
for arg in "$@"; do
    case "$arg" in
        --with-docker)
            INSTALL_DOCKER=1
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--with-docker]"
            exit 1
            ;;
    esac
done

echo "=== KoroMind Setup ==="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

if [ "${INSTALL_DOCKER}" -eq 1 ]; then
    SYS_STEP="1/6"
    DOCKER_STEP="2/6"
    UV_STEP="3/6"
    REPO_STEP="4/6"
    VENV_STEP="5/6"
    ENV_STEP="6/6"
    SYSTEMD_STEP=""
else
    SYS_STEP="1/6"
    DOCKER_STEP=""
    UV_STEP="2/6"
    REPO_STEP="3/6"
    VENV_STEP="4/6"
    ENV_STEP="5/6"
    SYSTEMD_STEP="6/6"
fi

install_docker() {
    echo -e "${YELLOW}[${DOCKER_STEP}] Installing Docker Engine + Compose plugin...${NC}"
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
}

# 1. Install system packages
echo -e "${YELLOW}[${SYS_STEP}] Installing system packages...${NC}"
sudo apt-get update
sudo apt-get install -y git python3 python3-venv curl build-essential

if [ "${INSTALL_DOCKER}" -eq 1 ]; then
    install_docker
fi

# 2. Install uv
echo -e "${YELLOW}[${UV_STEP}] Installing uv...${NC}"
# Use Astral's installer to avoid pip PEP 668 issues on Debian/Ubuntu.
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Add to PATH permanently if not already there
if ! grep -q '.local/bin' ~/.profile 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.profile
fi

# 3. Clone repo if not already in it
echo -e "${YELLOW}[${REPO_STEP}] Setting up repository...${NC}"
if [ ! -f "pyproject.toml" ]; then
    git clone https://github.com/KoroMind/KoroMind.git
    cd KoroMind
fi
REPO_DIR=$(pwd)

# 4. Create venv and install dependencies
echo -e "${YELLOW}[${VENV_STEP}] Creating virtual environment and installing dependencies...${NC}"
uv venv -p python3
source .venv/bin/activate
uv sync --frozen

# 5. Create .env if it doesn't exist
echo -e "${YELLOW}[${ENV_STEP}] Setting up configuration...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
else
    echo ".env already exists, skipping"
fi

# 6. Create systemd service for Telegram bot
if [ "${INSTALL_DOCKER}" -ne 1 ]; then
echo -e "${YELLOW}[${SYSTEMD_STEP}] Creating systemd service...${NC}"
sudo tee /etc/systemd/system/koromind-telegram.service > /dev/null <<EOF
[Unit]
Description=KoroMind Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$REPO_DIR
EnvironmentFile=$REPO_DIR/.env
ExecStart=$REPO_DIR/.venv/bin/python -m koro telegram
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
fi

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
echo ""
if [ "${INSTALL_DOCKER}" -eq 1 ]; then
    echo ""
    echo "2. Start with Docker Compose:"
    echo "   docker compose -f $REPO_DIR/docker-compose.yml up -d --build"
    echo ""
    echo "3. Check logs:"
    echo "   docker compose -f $REPO_DIR/docker-compose.yml logs -f koro"
    echo ""
    echo "Docker was installed and enabled."
    echo "If 'docker' is still denied for your user, reconnect SSH or run: newgrp docker"
else
    echo "2. Start the service:"
    echo "   sudo systemctl enable --now koromind-telegram"
    echo ""
    echo "3. Check logs:"
    echo "   sudo journalctl -u koromind-telegram -f"
fi
echo ""
