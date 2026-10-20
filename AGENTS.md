# RiceFlow backend agent guide

RiceFlow is a Django REST Framework backend for rice farmers in Panabo City. It serves the RiceFlow mobile and web apps: farm registration and location checks, environmental scans, rice variety recommendations, planting guides, crop progress, yield prediction, and an AI chat.

## Stack

- Python, Django 4.2, Django REST Framework 3.15, SimpleJWT
- PostgreSQL through `DATABASE_URL` (`dj-database-url`, `psycopg2-binary`)
- scikit-learn, NumPy, pandas, and joblib for K-Means clustering and Linear Regression
- Gemini API for the AI chat (`GEMINI_API_KEY`)

## Project skills

- For API endpoints, serializers, URL routes, permissions, or JWT auth, read [RiceFlow API endpoints](.agents/skills/riceflow-api-endpoints/SKILL.md).
- For yield prediction, K-Means clustering, RSI scoring, fit explanations, model training, or land-data checks, read [RiceFlow ML predictions](.agents/skills/riceflow-ml-predictions/SKILL.md).
- For writing or reviewing Python tests, consult [Python testing patterns](.agents/skills/python-testing-patterns/SKILL.md). It uses pytest examples; this project runs tests with `python manage.py test`, so adapt the patterns to Django's test runner.

## Layout

| Location | Responsibility |
|---|---|
| `config/` | Settings, root URLs, WSGI/ASGI |
| `apps/accounts/` | Custom `User` model, registration, login, JWT |
| `apps/farms/` | Farms, Panabo location checks, `load_land_data` |
| `apps/environmental/` | Environmental scans per farm |
| `apps/varieties/` | Rice variety catalog and seed data |
| `apps/recommendations/` | RSI scoring, K-Means clustering, fit explanations |
| `apps/guides/` | Planting guides and guide steps |
| `apps/progress/` | Farm cycles, stages, yield records |
| `apps/predictions/` | Linear Regression yield prediction |
| `apps/ai/` | Gemini-backed AI chat |
| `notebooks/` | Model training notebook and charts |
| `API_REFERENCE.md`, `API_DEMO_GUIDE.md` | Endpoint contracts and demo steps |

## Working rules

- Before editing, check the current branch, working tree, and recent commits. Preserve unrelated changes and never commit `.env`.
- Trace the affected route, view, serializer, and service before changing them. Reuse existing helpers before adding new ones.
- Keep URLs (with trailing slashes), methods, request fields, response keys, status codes, and permissions unchanged unless changing them is the task.
- Keep changes small. Add or update a focused test for behavior changes and run `python manage.py test` for the affected app.
- Before opening a PR, run the CI checks locally: `ruff check .`, `python manage.py makemigrations --check --dry-run`, and `python manage.py test`. Follow the branching and Conventional Commits rules in `README.md`.
- Keep secrets in `.env` and generated model files (`*.pkl`, `*.npz`, `models/trained/`) out of git.
- Report checks that failed or were not run separately from checks that passed.
