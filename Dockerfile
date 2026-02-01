# KoroMind - Production Docker Image
# Multi-stage build for efficient image size

# ============================================================================
# Stage 1: Base with Node.js and Python 3.12
# ============================================================================
FROM node:20-slim AS base

# Install Python 3.12 and system dependencies
# Note: We need Python 3.12+ for Pydantic + TypedDict compatibility
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    && echo "deb http://deb.debian.org/debian trixie main" > /etc/apt/sources.list.d/trixie.list \
    && apt-get update && apt-get install -y -t trixie \
    python3.12 \
    python3.12-venv \
    && rm -rf /var/lib/apt/lists/* \
    && rm /etc/apt/sources.list.d/trixie.list \
    && ln -sf /usr/bin/python3.12 /usr/bin/python3

# Create non-root user (uid 1000 required by Claude CLI)
# Delete existing node user first (it has UID 1000)
RUN userdel -r node && \
    useradd -m -u 1000 -s /bin/bash claude && \
    mkdir -p /home/claude/.claude && \
    chown -R claude:claude /home/claude

# ============================================================================
# Stage 2: Application Setup
# ============================================================================
FROM base AS app

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Switch to non-root user
USER claude
WORKDIR /home/claude/app

# Copy dependency manifests first for better caching
COPY --chown=claude:claude pyproject.toml uv.lock ./

# Create virtual environment and install dependencies via uv
RUN python3.12 -m venv .venv && \
    .venv/bin/pip install --no-cache-dir --upgrade pip uv && \
    .venv/bin/uv sync --frozen --no-dev

# Copy application code
COPY --chown=claude:claude src/ ./src/

# Copy Claude settings (agents, skills, config from toru-claude-settings submodule)
COPY --chown=claude:claude .claude-settings/ /home/claude/.claude/

# Create necessary directories
RUN mkdir -p /home/claude/sandbox /home/claude/state

# ============================================================================
# Runtime Configuration
# ============================================================================

# Health check - verify bot can start
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD pgrep -f "python.*bot.py" || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    CLAUDE_WORKING_DIR=/home/claude/app \
    CLAUDE_SANDBOX_DIR=/home/claude/sandbox \
    PATH="/home/claude/app/.venv/bin:$PATH"

# Default command
CMD ["python", "src/bot.py"]
