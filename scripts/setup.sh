#!/bin/bash
# KoroMind Setup Script
# Automates Docker-first setup on a fresh Debian/Ubuntu VM (GCP, AWS, or any Linux box)
set -e

echo "=== KoroMind Setup ==="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VAULT_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --vault-only)
            VAULT_ONLY=1
            ;;
        -h|--help)
            echo "Usage: $0 [--vault-only]"
            echo "  --vault-only  Only scaffold the second-brain vault; skip package/docker/.env setup"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: $0 [--vault-only]"
            exit 1
            ;;
    esac
done

install_docker() {
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
        sudo tee /usr/local/bin/docker-compose > /dev/null <<'EOL'
#!/bin/sh
exec docker compose "$@"
EOL
        sudo chmod +x /usr/local/bin/docker-compose
    fi
}

setup_system_packages() {
    echo -e "${YELLOW}[1/5] Installing system packages...${NC}"

    if [ "$VAULT_ONLY" -eq 1 ]; then
        echo "Vault-only mode: skipping system package installation."
        return
    fi

    if command -v git >/dev/null 2>&1 && command -v curl >/dev/null 2>&1; then
        echo "git and curl already installed, skipping."
        return
    fi

    if ! command -v apt-get >/dev/null 2>&1; then
        echo "Warning: apt-get not found; cannot auto-install git/curl."
        return
    fi

    sudo apt-get update
    sudo apt-get install -y git curl
}

setup_docker() {
    echo -e "${YELLOW}[2/5] Installing Docker Engine + Compose plugin...${NC}"

    if [ "$VAULT_ONLY" -eq 1 ]; then
        echo "Vault-only mode: skipping Docker installation."
        return
    fi

    if command -v docker >/dev/null 2>&1 && \
       (docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1); then
        echo "Docker and Compose already installed, skipping."
        return
    fi

    if ! command -v apt-get >/dev/null 2>&1; then
        echo "Warning: apt-get not found; cannot auto-install Docker."
        return
    fi

    install_docker
}

setup_repository() {
    echo -e "${YELLOW}[3/5] Setting up repository...${NC}"

    if [ ! -x "$(command -v git)" ]; then
        echo "Error: git is required but not installed."
        exit 1
    fi

    if [ -f "pyproject.toml" ] && [ -d "scripts/second-brain-template" ]; then
        REPO_DIR="$(pwd)"
    elif [ -n "${KOROMIND_REPO_DIR:-}" ] && [ -f "${KOROMIND_REPO_DIR}/pyproject.toml" ]; then
        REPO_DIR="$(cd "${KOROMIND_REPO_DIR}" && pwd)"
    elif [ -f "$HOME/KoroMind/pyproject.toml" ]; then
        REPO_DIR="$HOME/KoroMind"
    elif [ -f "./KoroMind/pyproject.toml" ]; then
        REPO_DIR="$(cd ./KoroMind && pwd)"
    else
        if [ -d "$HOME/KoroMind" ] && [ ! -f "$HOME/KoroMind/pyproject.toml" ]; then
            echo "Error: $HOME/KoroMind exists but does not look like a KoroMind repo."
            echo "Set KOROMIND_REPO_DIR to your repo path or remove $HOME/KoroMind and rerun."
            exit 1
        fi

        git clone https://github.com/KoroMind/KoroMind.git "$HOME/KoroMind"
        REPO_DIR="$HOME/KoroMind"
    fi

    cd "$REPO_DIR"
    echo "Using repository: $REPO_DIR"
}

setup_submodule() {
    if [ "$VAULT_ONLY" -eq 1 ]; then
        return
    fi

    # Ensure required submodules are present for Docker build context.
    git config submodule.".claude-settings".url https://github.com/ToruAI/toru-claude-settings.git || true
    git submodule sync --recursive
    if ! git submodule update --init --recursive; then
        echo "Warning: failed to fetch .claude-settings submodule; creating local fallback directory."
    fi
    if [ ! -d ".claude-settings" ] || [ -z "$(ls -A .claude-settings 2>/dev/null)" ]; then
        mkdir -p .claude-settings
        cat > .claude-settings/README.md <<'EOL'
Fallback Claude settings directory created by setup script.
If you have access to the settings submodule, run:
git submodule update --init --recursive
EOL
    fi
}

setup_env_file() {
    echo -e "${YELLOW}[4/5] Setting up configuration...${NC}"

    if [ "$VAULT_ONLY" -eq 1 ]; then
        echo "Vault-only mode: skipping .env setup."
        return
    fi

    if [ ! -f .env ]; then
        cp .env.example .env
        echo "Created .env from .env.example"
    else
        echo ".env already exists, skipping"
    fi
}

scaffold_second_brain() {
    echo -e "${YELLOW}[5/5] Scaffolding second-brain vault...${NC}"
    VAULT_TEMPLATE_DIR="$REPO_DIR/scripts/second-brain-template"
    VAULT_DIR="$HOME/koromind-work-dir/second-brain"

    mkdir -p "$HOME/koromind-work-dir" "$HOME/koromind-sandbox" "$VAULT_DIR"

    if [ -d "$VAULT_TEMPLATE_DIR" ]; then
        cp -a -n "$VAULT_TEMPLATE_DIR/." "$VAULT_DIR/"
        echo "Second-brain template synced to $VAULT_DIR (existing files preserved)."
    else
        echo "Warning: second-brain template not found at $VAULT_TEMPLATE_DIR; skipping scaffold."
    fi
}

setup_system_packages
setup_docker
setup_repository
setup_submodule
setup_env_file
scaffold_second_brain

echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""

if [ "$VAULT_ONLY" -eq 1 ]; then
    echo "Vault-only mode completed."
    echo "Second brain vault is ready at: $HOME/koromind-work-dir/second-brain"
    echo ""
    echo "To run full server setup later:"
    echo "  cd $REPO_DIR && bash scripts/setup.sh"
    echo ""
    exit 0
fi

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
echo "4. Open your ready-to-use second brain vault:"
echo "   $HOME/koromind-work-dir/second-brain"
echo ""
echo "Docker was installed and enabled."
echo "If 'docker' is still denied for your user, reconnect SSH or run: newgrp docker"
echo ""
