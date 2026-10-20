## What changed

<!-- One or two sentences. Link the issue: Closes #123 -->

## Type

- [ ] feat: new feature
- [ ] fix: bug fix
- [ ] docs / test / chore / refactor / ci

## How it was tested

- [ ] `python manage.py test` passes
- [ ] `ruff check .` passes
- [ ] `python manage.py makemigrations --check` shows no missing migrations
- [ ] Tried the changed endpoint (Postman or the app)

## Checklist

- [ ] PR title follows Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`)
- [ ] Targets `develop` (only release and hotfix PRs target `main`)
- [ ] No secrets, `.env` values, or trained model files committed
- [ ] `API_REFERENCE.md` updated if an endpoint changed
