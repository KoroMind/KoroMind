# Suggested commands
- Setup venv: `python -m venv .venv` then `source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Run bot: `python bot.py`
- Run tests: `pytest -v` (tests live in `tests/`; CONTRIBUTING.md references `pytest test_bot.py -v` which may be outdated)
- Coverage: `pytest --cov=bot --cov-report=term-missing`
- Docker: `docker-compose up -d` (after `cp docker/koro.env.example docker/koro.env` and editing env)
- Logs (docker): `docker-compose logs -f koro`
- Utility (Darwin): `ls`, `pwd`, `cd`, `rg`, `find`, `git status`, `git diff`
