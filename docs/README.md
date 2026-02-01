# KoroMind Documentation

This directory contains comprehensive documentation for KoroMind development and testing.

## Documentation Files

### Testing

- **[e2e-testing.md](e2e-testing.md)** - End-to-End testing guide for Telegram bot
  - How to set up bot-to-bot testing
  - Running E2E tests
  - CI/CD integration
  - Troubleshooting

## Quick Links

### For Users
- [Main README](../README.md) - Project overview and setup
- [Environment Setup](../.env.example) - Configuration options

### For Developers
- [Testing Guide](../AGENTS.md#testing) - All test types
- [Project Architecture](../AGENTS.md#architecture) - Package structure
- [Development Workflow](../.ai/specs/AGENTS.md) - Spec-driven development

### For Contributors
- [Code Style](../AGENTS.md#code-style) - Python best practices
- [Git Workflow](../AGENTS.md#documentation-and-specifications) - Branch and commit conventions

## Test Categories

KoroMind has three test levels:

1. **Unit Tests** (`src/tests/unit/`)
   - Fast, isolated component tests
   - No external dependencies
   - Run with: `pytest src/tests/unit -v`

2. **Integration Tests** (`src/tests/integration/`)
   - Test component interactions
   - May require API keys
   - Marked with `@pytest.mark.live` if they need real APIs
   - Run with: `pytest src/tests/integration -v`

3. **E2E Tests** (`src/tests/e2e/`)
   - Full system tests via Telegram
   - Require test bot setup
   - Marked with `@pytest.mark.e2e`
   - Run with: `pytest src/tests/e2e -v`
   - See [e2e-testing.md](e2e-testing.md) for setup

## Running Tests Selectively

```bash
# All tests
pytest -v

# Skip E2E tests
pytest -m "not e2e" -v

# Skip tests requiring live APIs
pytest -m "not live" -v

# Skip both
pytest -m "not live and not e2e" -v

# Only E2E tests
pytest -m e2e -v

# Only live integration tests
pytest -m live -v

# Unit tests only (fastest)
pytest src/tests/unit -v
```

## Adding Documentation

When adding new features or significant changes:

1. Update relevant documentation files
2. Add examples where helpful
3. Update this README if adding new doc files
4. Keep docs in sync with code changes
