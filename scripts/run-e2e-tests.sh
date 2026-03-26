#!/bin/bash
# Run E2E tests for KoroMind Telegram bot
# Usage: ./scripts/run-e2e-tests.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}KoroMind E2E Test Runner${NC}"
echo "======================================"

# Check if .env.test exists
if [ ! -f ".env.test" ]; then
    echo -e "${RED}ERROR: .env.test not found${NC}"
    echo "Copy .env.test.example to .env.test and configure your test credentials."
    echo "See docs/e2e-testing.md for setup instructions."
    exit 1
fi

# Load test environment
echo -e "${YELLOW}Loading test environment...${NC}"
set -a; source .env.test; set +a

# Verify required variables
if [ -z "$KOROMIND_BOT_TOKEN" ] || [ -z "$TEST_BOT_TOKEN" ] || [ -z "$TEST_CHAT_ID" ]; then
    echo -e "${RED}ERROR: Missing required environment variables${NC}"
    echo "Required: KOROMIND_BOT_TOKEN, TEST_BOT_TOKEN, TEST_CHAT_ID"
    exit 1
fi

echo -e "${GREEN}✓ Environment configured${NC}"

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    else
        echo -e "${RED}ERROR: Virtual environment not found${NC}"
        echo "Run: uv venv && source .venv/bin/activate && uv sync --extra dev"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Virtual environment active${NC}"

# Check if bot is running
echo ""
echo -e "${YELLOW}NOTE: Make sure KoroMind bot is running before continuing${NC}"
echo "Start the bot in another terminal with:"
echo "  python -m koro telegram"
echo "Or using Docker:"
echo "  docker compose up -d koro"
echo ""
read -p "Is the bot running? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Start the bot and try again."
    exit 1
fi

echo -e "${GREEN}✓ Bot is running${NC}"
echo ""

# Run tests
echo -e "${GREEN}Running E2E tests...${NC}"
echo "======================================"

if [ -z "$1" ]; then
    # Run all E2E tests
    pytest src/tests/e2e/test_telegram_e2e.py -v
else
    # Run specific test
    pytest "src/tests/e2e/test_telegram_e2e.py::$1" -v
fi

EXIT_CODE=$?

echo ""
echo "======================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
fi

exit $EXIT_CODE
