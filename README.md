# RiceFlow Backend

[![CI](https://github.com/microxxd300/rice_flow_backend/actions/workflows/ci.yml/badge.svg)](https://github.com/microxxd300/rice_flow_backend/actions/workflows/ci.yml)
[![CodeQL](https://github.com/microxxd300/rice_flow_backend/actions/workflows/codeql.yml/badge.svg)](https://github.com/microxxd300/rice_flow_backend/actions/workflows/codeql.yml)

Django REST Framework API for RiceFlow, a rice farming assistant for Panabo City. It serves the RiceFlow mobile app and admin dashboard: farms, environmental scans, variety recommendations (RSI scoring + K-Means), planting guides, crop progress, yield prediction (Linear Regression), and an AI chat.

Endpoint details: [API_REFERENCE.md](API_REFERENCE.md). Demo steps: [API_DEMO_GUIDE.md](API_DEMO_GUIDE.md).

## Local setup

```bash
python -m venv venv
venv\Scripts\activate            # Windows (macOS/Linux: source venv/bin/activate)
pip install -r requirements-dev.txt
copy .env.example .env           # then fill in your own values
python manage.py migrate
python manage.py runserver
```

Run the same checks as CI before opening a pull request:

```bash
ruff check .
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Run the full stack with Docker

Runs the admin frontend (nginx), this backend (gunicorn), PostgreSQL, and Redis. Clone [rice_flow_admin](https://github.com/microxxd300/rice_flow_admin) next to this repo first.

```bash
copy .env.docker.example .env.docker   # set SECRET_KEY, POSTGRES_PASSWORD, and the same password in DATABASE_URL
docker compose up --build -d --wait
```

Open http://localhost:8080. Only that port is published: nginx serves the React app and proxies `/api`, `/admin`, and `/static` to Django. The backend, database, and Redis are reachable only inside the Compose network. On start, the backend runs `migrate` and `collectstatic`, then gunicorn.

| Command | What it does |
|---|---|
| `docker compose ps` | Container status and health |
| `docker compose logs -f backend` | Follow backend logs |
| `docker compose down` | Stop the stack (database data is kept) |
| `docker compose down -v` | Stop and delete the database volume |

## Branching strategy

| Branch | Purpose | Protected |
|---|---|---|
| `main` | Production code. Every merge deploys. | Yes |
| `develop` | Integration and staging. Features merge here first. | Yes |
| `feature/<name>` | New work, branched from `develop` | No |
| `fix/<name>` | Bug fixes, branched from `develop` | No |
| `hotfix/<name>` | Urgent production fixes, branched from `main`, merged into `main` and `develop` | No |

**Rules for `main` and `develop`:** changes arrive only through pull requests, each PR needs at least 1 approval and passing CI, and direct commits and force pushes are blocked.

**Flow:**

1. `git switch develop && git pull`
2. `git switch -c feature/<name>`
3. Commit using Conventional Commits, push, and open a PR into `develop`
4. When `develop` is ready to release, open a PR from `develop` into `main`
5. After merging to `main`, tag the release: `git tag v1.2.0 && git push origin v1.2.0`

**Commit messages** follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`, `ci:`. Example: `fix(farms): reject pins outside Panabo`.

**Releases** use [semantic version](https://semver.org/) tags: `vMAJOR.MINOR.PATCH` (for example `v1.0.0`).

## CI/CD

| Workflow | Runs on | What it does |
|---|---|---|
| [CI](.github/workflows/ci.yml) | Every push and PR | ruff, missing-migration check, tests on Postgres + Redis, coverage report, `check --deploy`, pip-audit, gitleaks |
| [CodeQL](.github/workflows/codeql.yml) | Pushes to `main`/`develop`, PRs, weekly | Static security analysis |
| [CD](.github/workflows/cd.yml) | After CI passes on `main` | Builds the Docker image, pushes it to GHCR, deploys to Render, waits for `/api/health/` to report the new commit |
| [Dependabot](.github/dependabot.yml) | Weekly | Update PRs for pip, Docker, and GitHub Actions |

Secrets (`SECRET_KEY`, `DATABASE_URL`, `GEMINI_API_KEY`, Supabase keys) live in `.env` locally and in the host's environment settings in production. They are never committed.
