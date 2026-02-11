#!/bin/bash
# KoroMind Setup Script
# Automates setup on a fresh Debian/Ubuntu VM (GCP, AWS, or any Linux box)
set -e

echo "=== KoroMind Setup ==="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Install system packages
echo -e "${YELLOW}[1/6] Installing system packages...${NC}"
sudo apt-get update
sudo apt-get install -y git python3 python3-venv curl build-essential

# 2. Install uv
echo -e "${YELLOW}[2/6] Installing uv...${NC}"
# Use Astral's installer to avoid pip PEP 668 issues on Debian/Ubuntu.
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Add to PATH permanently if not already there
if ! grep -q '.local/bin' ~/.profile 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.profile
fi

# 3. Clone repo if not already in it
echo -e "${YELLOW}[3/6] Setting up repository...${NC}"
if [ ! -f "pyproject.toml" ]; then
    git clone https://github.com/KoroMind/KoroMind.git
    cd KoroMind
fi
REPO_DIR=$(pwd)

# 4. Create venv and install dependencies
echo -e "${YELLOW}[4/6] Creating virtual environment and installing dependencies...${NC}"
uv venv -p python3
source .venv/bin/activate
uv sync --frozen

# 5. Create .env if it doesn't exist
echo -e "${YELLOW}[5/6] Setting up configuration...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
else
    echo ".env already exists, skipping"
fi

# 6. Create systemd service for Telegram bot
echo -e "${YELLOW}[6/6] Creating systemd service...${NC}"
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
echo "2. Start the service:"
echo "   sudo systemctl enable --now koromind-telegram"
echo ""
echo "3. Check logs:"
echo "   sudo journalctl -u koromind-telegram -f"
echo ""
