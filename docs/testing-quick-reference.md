# Testing Quick Reference

Quick reference for running KoroMind tests.

## Test Structure

```
src/tests/
├── unit/              # Fast, isolated tests (no external APIs)
├── integration/       # Component interaction tests (may need API keys)
└── e2e/              # End-to-end Telegram bot tests (needs setup)
```

## Common Commands

### Run All Tests
```bash
pytest -v
```

### Run by Test Type
```bash
pytest src/tests/unit -v              # Unit tests only
pytest src/tests/integration -v       # Integration tests
pytest src/tests/e2e -v               # E2E tests (needs setup)
```

### Run by Marker
```bash
pytest -m "not e2e" -v                # Skip E2E
pytest -m "not live" -v               # Skip live API tests
pytest -m "not live and not e2e" -v   # Skip both
pytest -m e2e -v                      # Only E2E
pytest -m live -v                     # Only live API tests
```

### Run Specific Test
```bash
pytest src/tests/unit/test_voice.py -v
pytest src/tests/unit/test_voice.py::test_transcribe_basic -v
```

### Coverage
```bash
pytest --cov=koro --cov-report=term-missing
pytest --cov=koro --cov-report=html    # HTML report in htmlcov/
```

## E2E Testing

### Setup (one-time)
1. Create test group in Telegram
2. Create tester bot with @BotFather
3. Get chat ID
4. Configure `.env.test`:
   ```bash
   cp .env.test.example .env.test
   # Edit .env.test with your credentials
   ```

### Running E2E Tests
```bash
# Start bot first
python -m koro telegram

# Then in another terminal:
./scripts/run-e2e-tests.sh           # All E2E tests
./scripts/run-e2e-tests.sh test_name # Specific test
```

See [e2e-testing.md](e2e-testing.md) for detailed setup.

## Test Markers

| Marker | Description | Skip with |
|--------|-------------|-----------|
| `live` | Requires live API keys | `-m "not live"` |
| `e2e` | End-to-end Telegram bot test | `-m "not e2e"` |
| `eval` | Agent-evaluated quality test | `-m "not eval"` |

## CI/CD

### GitHub Actions
```yaml
# Skip E2E and live tests in CI
pytest -m "not live and not e2e" -v
```

### Pre-commit (Local)
```bash
pre-commit run --all-files           # Linting only
pytest src/tests/unit -v             # Fast tests
```

## Debugging

### Verbose Output
```bash
pytest -vv                           # Extra verbose
pytest -vv -s                        # Show print statements
pytest --log-cli-level=DEBUG         # Show debug logs
```

### Run Specific Test with Debugging
```bash
pytest src/tests/unit/test_voice.py::test_name -vv -s
```

### Profile Tests
```bash
pytest --durations=10                # Show 10 slowest tests
```

## Environment Variables

### Required for Integration Tests
- `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`
- `ELEVENLABS_API_KEY`

### Required for E2E Tests
- `KOROMIND_BOT_TOKEN`
- `TEST_BOT_TOKEN`
- `TEST_CHAT_ID`

### Optional
- `LOG_LEVEL` - Set to `DEBUG` for verbose output
- `PYTEST_CURRENT_TEST` - Auto-set by pytest

## Common Issues

### Tests Skip Unexpectedly
Check if required environment variables are set:
```bash
echo $ANTHROPIC_API_KEY
echo $ELEVENLABS_API_KEY
```

### E2E Tests Timeout
- Ensure bot is running
- Verify bot is in test group
- Check `ALLOWED_CHAT_ID` includes test group
- Increase timeout in test code

### Import Errors
```bash
# Reinstall dependencies
uv sync --extra dev

# Verify installation
python -c "import koro; print('OK')"
```

## Additional Resources

- [e2e-testing.md](e2e-testing.md) - E2E testing guide
- [AGENTS.md](../AGENTS.md) - Full development guide
- [pytest docs](https://docs.pytest.org/) - pytest documentation
