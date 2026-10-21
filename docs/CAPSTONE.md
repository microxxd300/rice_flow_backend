# RiceFlow: capstone checklist

What each requirement needed, what was done, and how to demo it. Covers the three repositories:

| Repo | What it is |
|---|---|
| [`rice_flow_backend`](https://github.com/microxxd300/rice_flow_backend) | Django REST API, PostgreSQL (Supabase), Redis, Docker |
| [`rice_flow_admin`](https://github.com/microxxd300/rice_flow_admin) | React + Vite admin dashboard, served by nginx |
| [`rice_flow_frontend_app`](https://github.com/microxxd300/rice_flow_frontend_app) | Expo (React Native) app for farmers |

**Status key:** ✅ done · 🟡 partly done · ⏭️ skipped on purpose (reason given) · ❌ not done

Items are marked ⏭️ only when doing them would not make RiceFlow safer or faster at its scale (one city's farmers and a few admins), or would break something that works.

---

## Quick demo script (about 10 minutes)

Run the backend locally (`python manage.py runserver`) and log in once to get a token: `POST /api/auth/login/` with `{"email": "...", "password": "..."}`. Use `Authorization: Bearer <access_token>` on the requests below.

| # | Show | How |
|---|---|---|
| 1 | Rate limiting | Send 11 wrong logins in a minute to `POST /api/auth/login/`. The 11th returns **429** with a `Retry-After` header |
| 2 | Caching | `GET /api/environmental/weather/?lat=7.30&lng=125.68` twice. Response header `X-Cache: MISS`, then `X-Cache: HIT`. The server console prints `cache MISS ...` / `cache HIT ...` |
| 3 | Pagination | `GET /api/farms/?page_size=5`. The response has `count`, `total_pages`, `next`, `previous`, `results` |
| 4 | Single-use refresh tokens | `POST /api/token/refresh/` with the refresh token: works. Same token again: **401** |
| 5 | Logout | `POST /api/auth/logout/` with `{"refresh": "..."}`, then try to refresh with it: **401** |
| 6 | Security log | The server console shows `login failed email=... ip=...`, `rate limited ...`, `permission denied ...` |
| 7 | Access control | Run `python manage.py test apps.progress apps.accounts`. These tests replay real attacks (making yourself admin, writing into another farmer's data) and expect them to fail |
| 8 | Deploy settings | `python manage.py check --deploy` with `DEBUG=False`: no issues |
| 9 | CI blocks bad merges | Any PR on GitHub: the required checks must pass before **Merge** is allowed |

---

## 1. Testing

| Requirement | Status | What was done / why not | How to demo |
|---|---|---|---|
| pytest, pytest-django, pytest-cov | ⏭️ | Kept Django's test runner and `coverage`, which CI already used. Switching changes tooling, not what is tested | `coverage run manage.py test && coverage report` |
| Backend unit tests | 🟡 | 47 backend tests: location check, serializers, pagination, caching, throttling, tokens, passwords, settings | `python manage.py test` |
| API tests: CRUD, validation, 401/403, one user can't touch another's data | 🟡 | Cross-user writes, self-promotion to admin, 403 on admin endpoints, validation errors on register. Full CRUD per endpoint is not covered | `python manage.py test apps.progress apps.accounts config` |
| Pagination, 429, caching tests | ✅ | `config/tests.py`, `config/test_throttling.py`, `apps/environmental/tests.py` | same as above |
| Frontend component tests | ❌ | Not done | |
| Frontend tests with the API mocked | 🟡 | Admin API client tests with `fetch` mocked (Vitest): auth header, caching, token refresh. No MSW | `npm test` in `rice_flow_admin` |
| End-to-end test (optional) | ❌ | Not done | |
| Coverage 70–80% | ❌ | Backend is at **47%** (was 39%) | `coverage report` |
| Tests run in CI and block merging | ✅ | Backend: lint, migrations check, tests, `check --deploy`, Docker build, pip-audit, gitleaks, CodeQL. Admin: lint, tests, build. Mobile: install + TypeScript check. All are required checks on protected branches | Open any PR |

## 2. Pagination

| Requirement | Status | What was done / why not | How to demo |
|---|---|---|---|
| Global `DEFAULT_PAGINATION_CLASS` and `PAGE_SIZE` | ✅ | `config.pagination.StandardPagination`, 20 per page | `GET /api/farms/` |
| `page_size_query_param` and `max_page_size` | ✅ | `?page_size=` up to 100; `?page_size=999999` returns 100 | `GET /api/farms/?page_size=999999` |
| `count`, `next`, `previous`, `results`, `total_pages` | ✅ | `total_pages` added; existing keys unchanged so the apps keep working | any list endpoint |
| Every paginated queryset ordered | ✅ | Every model sets `Meta.ordering` | |
| CursorPagination for feeds/logs | ⏭️ | It removes `count` and `?page=`, which the mobile app reads. Lists are small | |
| django-filter | ⏭️ | The admin filters in the browser; lists are small | |
| Frontend pagination component | 🟡 | Admin lists have prev/next and page numbers; no page-size picker | Admin → Farms |
| Current page in the URL | ❌ | Not done | |
| Changing a filter resets to page 1 | ✅ | Admin Farms and Datasets pages | change a filter on page 2 |
| Loading and empty states | ✅ | Present on the admin list pages | |

## 3. Caching

| Requirement | Status | What was done / why not | How to demo |
|---|---|---|---|
| Redis as Django's cache | ✅ | Used when `REDIS_URL` is set (Docker Compose sets it); in-memory cache otherwise | `docker compose up` |
| Expensive GET endpoints cached | ✅ | Outside APIs, cached per location: hourly weather 10 min, weekly weather 30 min, rainfall 1 day, elevation and soil 30 days. A rescan of the same farm skips them. Measured: 1.7 s uncached vs 0.001 s cached | Demo #2 |
| Invalidation on save/delete | ⏭️ | Only outside-API data is cached, and it expires on a timer. Nothing from our own database is cached | |
| Per-user cache keys | ✅ | Not needed: weather and soil are the same for everyone at a location, and no user data is cached | |
| Failures not cached; Redis down doesn't break the app | ✅ | Errors are never stored; if Redis is unreachable the API calls the outside service directly | `apps/environmental/tests.py` |
| `select_related` / `prefetch_related` | 🟡 | Used in 18 places (e.g. farm cycles). No full N+1 audit | |
| TanStack Query | ⏭️ | The admin API client already caches GETs (60 s, cleared on any write, shared in-flight requests) | |
| nginx: hashed assets for a year, `index.html` no-cache | ✅ | `rice_flow_admin/nginx.conf` | `curl -I` on `/` and on a file in `/assets/` |
| Proof for the demo | ✅ | `X-Cache: HIT/MISS` header plus console log lines | Demo #2 |

## 4. Backend security

| Requirement | Status | What was done / why not | How to demo |
|---|---|---|---|
| Short access token, refresh rotation + blacklist, logout | ✅ | Access 30 min (was 1 day), refresh 7 days, each refresh token works once, `POST /api/auth/logout/` | Demos #4, #5 |
| Argon2 hashing | ✅ | Argon2 first; old PBKDF2 hashes upgrade on next login | Django admin → a user created or logged in since the change shows `argon2` in the password field |
| Strong password validators | ✅ | Register now runs Django's validators (they were configured but never called) | Register with `password123`: 400 |
| django-axes lockout | ⏭️ | Login rate limiting covers password guessing | |
| Rate limiting (anon/user/scoped, `NUM_PROXIES`, 429 + `Retry-After`) | ✅ | Login 10/min, register 10/hour, AI chat 60/hour, 300/hour anonymous, 3000/hour per user. Real client IP behind nginx/Render/ngrok, and a faked `X-Forwarded-For` doesn't help | Demo #1 |
| nginx `limit_req` | ❌ | Not done; Django rate limiting covers the API | |
| Default `IsAuthenticated`, role-based permissions | ✅ | Default in `REST_FRAMEWORK`; admin endpoints use `IsAdminUser`; roles: farmer, agriculturist (staff), admin (superuser) | Farmer token on `/api/auth/users/`: 403 |
| Object-level permissions / no IDOR | ✅ | Reads were already filtered by `request.user`. **Fixed:** farmers could create or move cycles, logs and yield records onto another farmer's farm | Demo #7 |
| **Fixed: privilege escalation** | ✅ | Any user could make themselves a superuser via `PATCH /api/auth/profile/`. `is_staff` / `is_superuser` are now read-only there | Demo #7 |
| Serializers with explicit fields | 🟡 | Every serializer farmers can write to is locked down; 11 read-only or admin-only serializers still use `fields='__all__'` | |
| File upload validation | ✅ | CSV import (admin only) checks file type; nginx caps request size at 20 MB | |
| XSS | ✅ | No `dangerouslySetInnerHTML` anywhere | |
| CSRF | ✅ | The API uses JWT headers (no cookies), so CSRF doesn't apply; Django admin keeps Django's CSRF protection | |
| HTTPS redirect, HSTS, secure cookies | ✅ | On when `DEBUG=False` | Demo #8 |
| Headers: nosniff, X-Frame-Options, Referrer-Policy | ✅ | Django's security middleware | `curl -I` an API URL |
| CSP, Permissions-Policy | ❌ | Not done; a CSP needs careful testing so the farm map tiles keep loading | |
| CORS restricted | ✅ | `CORS_ALLOWED_ORIGINS` from the environment; all origins only in `DEBUG` | `config/test_env_settings.py` |
| Secrets and hosts from env; `check --deploy` passes | ✅ | `SECRET_KEY` is required; nothing secret in git (gitleaks runs in CI) | Demo #8 |
| Custom admin URL | ✅ | `DJANGO_ADMIN_URL` (must start with `admin/`); plain `/admin/` then returns 404 | set it in `.env` |
| Custom exception handler, no stack traces | ✅ | Unexpected errors return `{"detail": "Server error."}` with status 500 | `config/test_security.py` |
| Log failed logins, throttles, permission denials | ✅ | `riceflow.security` logger | Demo #6 |
| Non-root container; DB and Redis not public | ✅ | Backend image runs as user `app`; only the frontend port is published | `docker-compose.yml` |
| Redis password | ❌ | Not done; Redis is reachable only inside the Docker network | |
| Dependency scanning | ✅ | Dependabot (to `develop`), pip-audit and CodeQL in CI | |
| Data Privacy Act (RA 10173) | ⏭️ | Deferred. Needed before launch: privacy notice and consent at sign-up, account deletion and data download, a named Data Protection Officer, and a breach plan (report to the NPC within 72 hours) | |

## 5. Admin web app security

| Requirement | Status | What was done / why not | How to demo |
|---|---|---|---|
| Access token in memory, refresh in httpOnly cookie | ⏭️ | Would need a cookie-based auth rewrite plus CSRF protection. The real risk it addresses is XSS, and there are no XSS openings. Tokens stay in `localStorage` | |
| Auto refresh | ✅ | On a 401 the client refreshes once and retries; parallel requests share one refresh | `src/services/api.test.js` |
| Inactivity logout | ❌ | Not done | |
| Clear cache on logout | ✅ | Logout clears the API cache and revokes the refresh token on the server | |
| No `dangerouslySetInnerHTML`, safe links | ✅ | None found; no `target="_blank"` without `noopener` | |
| No secrets in `VITE_` env, no prod source maps, no console logs | ✅ | Only `VITE_API_URL`; Vite builds without source maps by default; 0 `console.log` calls | |
| Protected and role-based routes | ✅ | Login gate plus per-role route guards | log in as an agriculturist |
| Handle 401 / 403 / 429 globally | 🟡 | 401 is handled globally (refresh or back to login). 403 and 429 show the server's message | |
| Error boundaries | ❌ | Not done | |
| zod / react-hook-form | ⏭️ | The backend validates every request | |
| npm audit + Dependabot, minimal third-party scripts | ✅ | `npm audit`: 0 issues; Dependabot on; no third-party scripts in `index.html` | `npm audit` |

## 6. Mobile app security

| Requirement | Status | What was done / why not | How to demo |
|---|---|---|---|
| Tokens in `expo-secure-store` | ✅ | iOS Keychain / Android Keystore. Tokens from older versions move over automatically | `src/services/tokenStorage.ts` |
| Wipe on logout | ✅ | Tokens deleted and refresh token revoked on the server | log out, then reopen the app |
| `allowBackup=false` | ✅ | Set in `app.json` | |
| HTTPS only | ✅ | API URL is HTTPS; Android release builds block plain HTTP by default, iOS has ATS | |
| Request timeouts | ✅ | 30 s on API requests, 5 s on the logout call | |
| No secrets in the bundle | ✅ | Only the API URL and environment name | |
| Hermes | ✅ | Expo's default engine | |
| R8 / ProGuard / shrinkResources | ⏭️ | Only matters for a store release build; deployment isn't approved yet | |
| Strip console logs | ❌ | 7 debug logs remain in the planting guide screen (IDs only, no tokens) | |
| Biometric confirmation | ⏭️ | No payments or other sensitive actions | |
| Handle 401 / 403 / 429 | 🟡 | 401 refreshes automatically; 403 and 429 show the server's message | |
| Minimal permissions | ✅ | Location only | `app.json` |
| Deep links validated | ✅ | The app registers no deep links | |
| WebView locked down | ✅ | The only WebView shows a built-in splash animation and loads no websites | |
| Vulnerable dependencies | 🟡 | Removed unused `axios`; `npm audit fix`: critical 2 → 0, total 54 → 42. The rest are in Expo / React Native build tools and need an Expo SDK upgrade. Dependabot on | `npm audit` |

## 7. Performance

| Requirement | Status | What was done / why not |
|---|---|---|
| Web: route-level code splitting | ✅ | Admin pages load with `React.lazy` |
| Web: API caching / prefetch | ✅ | Admin GET cache, plus a prefetch of the main pages right after login |
| Web: bundle analysis, virtualized lists, debounced search, image and font tuning | ❌ | Not done |
| Web: Lighthouse before/after | ❌ | Not measured |
| Mobile: FlashList, MMKV query cache, Reanimated, expo-image, release optimizations | ⏭️ | Lists are small (a farmer has a few farms and cycles). Release optimizations wait for an approved store build |
| Mobile: startup time before/after | ❌ | Not measured |
| Backend: caching slow outside APIs | ✅ | See section 3 (1.7 s → 0.001 s per cached lookup) |

---

## Known gaps (honest list)

- Coverage is 47%, below the 70–80% target. No frontend component tests or end-to-end tests.
- No CSP / Permissions-Policy header, no Redis password, no nginx `limit_req`.
- Admin tokens are in `localStorage` (decision explained in section 5). No inactivity logout, no error boundary.
- 42 dependency advisories remain in the mobile app's Expo / React Native build tooling until an Expo SDK upgrade.
- Data Privacy Act steps are not implemented yet.
- Production deployment (Render) is waiting for approval; CD already builds and publishes the Docker image.
