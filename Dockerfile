# KoroMind - Production Docker Image
# Multi-stage build for efficient image size

# ============================================================================
# Stage 1: Base with Python 3.12 and Node.js
# ============================================================================
FROM python:3.12-slim-bookworm AS base

# Install Node.js and system dependencies
# Note: We need Python 3.12+ for Pydantic + TypedDict compatibility
RUN apt-get update && apt-get install -y \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (uid 1000 required by Claude CLI)
RUN if id -u node >/dev/null 2>&1; then userdel -r node; fi && \
    useradd -m -u 1000 -s /bin/bash claude && \
    mkdir -p /home/claude/.claude && \
    chown -R claude:claude /home/claude

# ============================================================================
# Stage 2: Application Setup
# ============================================================================
FROM base AS app

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Install dev dependencies when requested
ARG INSTALL_DEV=false

# Switch to non-root user
USER claude
WORKDIR /home/claude/app

# Copy dependency manifests first for better caching
COPY --chown=claude:claude pyproject.toml uv.lock ./

# Copy application code (needed for editable install during uv sync)
COPY --chown=claude:claude src/ ./src/

# Create virtual environment and install dependencies via uv
RUN python -m venv .venv && \
    .venv/bin/pip install --no-cache-dir --upgrade pip uv && \
    if [ "$INSTALL_DEV" = "true" ]; then \
        .venv/bin/uv sync --frozen --extra dev; \
    else \
        .venv/bin/uv sync --frozen --no-dev; \
    fi

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
