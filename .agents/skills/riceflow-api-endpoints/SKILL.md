---
name: riceflow-api-endpoints
description: Use when adding or changing RiceFlow Django REST endpoints, serializers, URL routes, permissions, or JWT auth under apps/ and config/urls.py.
---

# RiceFlow API endpoints

## When to use

Use this skill for work on the Django REST Framework API that the RiceFlow mobile and web apps call: accounts and JWT auth, farms, environmental scans, varieties, recommendations, guides, progress, predictions, and the AI chat. Start at `config/urls.py`, find the app that owns the `api/<app>/` prefix, and trace into its `urls.py`, `views.py`, and `serializers.py`.

## Workflow

1. Locate the route in `config/urls.py` and the app's `urls.py`. Read the view and its serializer, then search for other callers of any helper you plan to change.
2. Check the documented contract in `API_REFERENCE.md` and `API_DEMO_GUIDE.md`. Keep the URL (including the trailing slash), HTTP method, request fields, response keys, status codes, and error shape the clients already depend on.
3. Keep the auth defaults from `config/settings.py`: SimpleJWT `JWTAuthentication`, `IsAuthenticated`, and `PageNumberPagination` with `PAGE_SIZE` 20. Use `IsAdminUser` only for admin actions such as model training and `/api/farms/all/`.
4. Scope user data to the requesting user. Follow the existing filters such as `Farm.objects.get(id=farm_id, user=request.user)` and `farm__user=request.user`, so one farmer cannot read or change another farmer's farms, scans, guides, or cycles.
5. Validate input in serializers or at the top of the view. Return `400` with an error message for bad input and `404` for objects the user does not own.
6. For model changes, add a migration with `python manage.py makemigrations <app>` and review it before committing. Do not edit migrations that are already on `main`.
7. Add or update a focused test (see `apps/farms/tests.py` for the `APIRequestFactory` and `force_authenticate` pattern). Run `python manage.py test apps.<app>`. For general test structure, consult [Python testing patterns](../python-testing-patterns/SKILL.md).
8. Update `API_REFERENCE.md` when an endpoint is added or its contract intentionally changes.

## Boundaries

- Keep secrets in `.env` (`DATABASE_URL`, `GEMINI_API_KEY`, `SUPABASE_*`). Never hardcode keys or commit `.env`.
- The AI chat in `apps/ai/views.py` calls Gemini over `requests`. Keep its timeout handling, its RiceFlow-only scope, and the "not configured" response when the key is missing.
- Do not widen `CORS_ALLOWED_ORIGINS` or set `CORS_ALLOW_ALL_ORIGINS` outside `DEBUG`.
- ML training, scoring, and model files belong to [RiceFlow ML predictions](../riceflow-ml-predictions/SKILL.md); views only call into those services.

## Useful result

A useful change names the route and view touched, states whether the request and response contract is unchanged or intentionally changed, shows the permission and ownership checks, and lists the tests run with their result.
