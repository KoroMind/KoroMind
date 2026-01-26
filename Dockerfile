# KoroMind - Production Docker Image
# Multi-stage build for efficient image size

# ============================================================================
# Stage 1: Base with Node.js and Python
# ============================================================================
FROM node:20-slim AS base

# Install Python and system dependencies
# Note: Debian bookworm has Python 3.11, which is compatible
RUN apt-get update && apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

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

# Copy requirements first for better caching
COPY --chown=claude:claude requirements.txt .

# Create virtual environment and install dependencies
RUN python3 -m venv .venv && \
    .venv/bin/pip install --no-cache-dir --upgrade pip && \
    .venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=claude:claude bot.py .
COPY --chown=claude:claude prompts/ ./prompts/

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
CMD ["python", "bot.py"]
