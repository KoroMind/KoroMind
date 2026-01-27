# Contributing to KoroMind

Thanks for your interest in contributing! This document outlines how to get started.

## Development Setup (Docker)

1. Clone the repository:
```bash
git clone https://github.com/KoroMind/KoroMind.git
cd KoroMind
```

2. Copy and configure environment:
```bash
cp .env.example .env
# Edit .env with your test credentials
```

3. Build and start the container:
```bash
docker compose up -d --build
```

4. View logs:
```bash
docker compose logs -f koro
```

## Development Setup (Local)

1. Install uv:
```bash
pip install uv
```

2. Create a virtual environment:
```bash
uv venv -p python3.11
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows
```

3. Install dependencies with uv:
```bash
uv sync --dev
```

4. Copy and configure environment:
```bash
cp .env.example .env
# Edit .env with your test credentials
```

## Running Tests

```bash
# Run all tests
pytest test_bot.py -v

# Run with coverage
pytest test_bot.py --cov=bot --cov-report=term-missing

# Run specific test
pytest test_bot.py::test_transcribe_voice -v
```

## Code Style

- Use Python 3.11+ features where appropriate
- Follow PEP 8 guidelines
- Add type hints for function signatures
- Keep functions focused and under 50 lines where possible

## Making Changes

1. **Create a branch** from `main`:
```bash
git checkout -b feat/your-feature-name
```

2. **Make your changes** with clear, focused commits

3. **Run tests** to ensure nothing breaks:
```bash
pytest test_bot.py -v
```

4. **Submit a pull request** with:
   - Clear description of what changed
   - Why the change is needed
   - Any breaking changes noted

## Pull Request Guidelines

- Keep PRs focused on a single change
- Update documentation if adding features
- Add tests for new functionality
- Ensure all tests pass before submitting

## Project Structure

```
KoroMind/
├── bot.py              # Main bot code
├── test_bot.py         # Test suite
├── prompts/            # Persona prompt files
│   └── koro.md
├── .env.example        # Environment template
├── settings.example.json  # Permissions template
└── pyproject.toml      # Dependencies and tool config
```

## Key Areas for Contribution

- **New features**: Tool integrations, UI improvements
- **Bug fixes**: Edge cases, error handling
- **Documentation**: Examples, tutorials, translations
- **Testing**: More test coverage, integration tests
- **Performance**: Optimization, caching

## Reporting Issues

When reporting bugs, please include:

1. Python version (`python --version`)
2. Operating system
3. Steps to reproduce
4. Expected vs actual behavior
5. Relevant log output

## Questions?

Open an issue with the `question` label or start a discussion.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
