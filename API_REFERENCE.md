# 🌾 RiceFlow Backend — API Reference for Defense

This file lives with the Django backend. Open it during defense if a panelist asks "show me where the data comes from."

---

## 🔑 YOUR BACKEND URL

```
https://doing-haven-requisite.ngrok-free.dev/api
```

⚠️ **This is an ngrok tunnel — only works while your tunnel is running.** Start your Django server + ngrok tunnel before defense.

---

## ⚠️ MUST-READ — Why Postman fails without these

If you ever get "Could not get any response", an HTML error page, or a strange 502 in Postman, **99% of the time it's one of these three:**

### 1. The `ngrok-skip-browser-warning` header

ngrok shows a "Visit Site" confirmation page that breaks API calls. Add this header to **every Postman request**:

| KEY | VALUE |
|---|---|
| `ngrok-skip-browser-warning` | `true` |

Your mobile app already sends this automatically. Postman does NOT.

### 2. Missing trailing slash `/`

Django is strict about URLs. **Always end with `/`**:
- ✅ `/api/auth/login/`
- ❌ `/api/auth/login`

### 3. Missing `Content-Type` header on POST/PUT

For any POST/PUT with a JSON body, add:

| KEY | VALUE |
|---|---|
| `Content-Type` | `application/json` |

### 4. List responses come in pages

List endpoints return 20 items per page, wrapped like this:

```json
{ "count": 105, "total_pages": 6, "next": "...?page=2", "previous": null, "results": [ ... ] }
```

Add `?page=2` for the next page, or `?page_size=50` for bigger pages (max 100).

### 5. `429 Too Many Requests`

Requests are rate limited. Wait the number of seconds in the `Retry-After` response header, then try again.

| What | Limit |
|---|---|
| Login | 10 per minute per IP |
| Register | 10 per hour per IP |
| Forgot password: send code | 10 per hour per IP |
| Forgot password: enter code | 20 per hour per IP |
| AI chat | 60 per hour per user |
| Anything else | 300 per hour logged out, 3000 per hour logged in |

### 6. Tokens expire: refresh and logout

- The `access_token` from login lasts **30 minutes**. After that, requests return `401`.
- Get a new one with `POST /api/token/refresh/` and body `{"refresh": "<refresh_token>"}`. The response has a new `access` **and a new `refresh`**. Save both: each refresh token works only once.
- Refresh tokens last **7 days**.
- Log out with `POST /api/auth/logout/` and body `{"refresh": "<refresh_token>"}`. That refresh token stops working right away.

---

## 📋 Table of contents

1. [How to log in (get a JWT token) — Postman step-by-step](#1-how-to-log-in-get-a-jwt-token)
2. [How to register a new user](#2-how-to-register-a-new-user)
3. [How to use the JWT token in other API calls](#3-how-to-use-the-jwt-token-in-other-api-calls)
4. [External APIs (SoilGrids, Open-Meteo, Nominatim)](#4-external-apis-no-jwt-required)
5. [Our backend APIs (every endpoint)](#5-our-backend-apis)
6. [Defense demo cheat sheet](#6-defense-demo-cheat-sheet)
7. [Summary table — at a glance](#7-summary-table--at-a-glance)
8. [Pre-defense checklist](#8-pre-defense-checklist)

---

# 1. How to log in (get a JWT token)

You need to do this in **TWO requests**. First login to get a token, then use that token for everything else.

---

## ✅ REQUEST 1 — LOGIN (to get a token)

### 1. Open Postman → click the `+` button to open a new tab

### 2. At the top, click the dropdown that says `GET` → change it to `POST`

### 3. Paste this in the URL bar (the long box next to POST):
```
https://doing-haven-requisite.ngrok-free.dev/api/auth/login/
```

### 4. Click the **Headers** tab (it's right below the URL bar)

Add these 2 rows by typing in the KEY and VALUE columns:

| KEY | VALUE |
|---|---|
| `ngrok-skip-browser-warning` | `true` |
| `Content-Type` | `application/json` |

### 5. Click the **Body** tab (next to Headers)

- Click the **`raw`** radio button
- On the far right, change the dropdown from `Text` to **`JSON`**

### 6. In the big body box, paste this (use YOUR real email and password):
```json
{
  "email": "your-real-email@example.com",
  "password": "your-real-password"
}
```

### 7. Click the blue **Send** button on the right

### 8. Look at the response panel at the bottom

You'll see something like:
```json
{
  "user": {...},
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjox...",
  "refresh_token": "..."
}
```

### 9. ⭐ COPY the `access_token` value

- Click on the long string after `"access_token":`
- Triple-click to select it all
- Press **Ctrl+C** to copy
- **Don't include the quotes**

---

## ✅ REQUEST 2 — ACCESS A PROTECTED ENDPOINT (using the token)

Example: getting the WLC weights at `/api/recommendations/rules/`

### 1. Click the `+` button again to open ANOTHER new tab

### 2. Leave the method as **`GET`** (don't change it)

### 3. Paste this URL:
```
https://doing-haven-requisite.ngrok-free.dev/api/recommendations/rules/
```

### 4. Click the **Headers** tab

Add these 2 rows:

| KEY | VALUE |
|---|---|
| `ngrok-skip-browser-warning` | `true` |
| `Authorization` | `Bearer ` + paste your token |

⚠️ **For the Authorization row:**
- Type the word `Bearer`
- Type one space
- Then paste the access_token you copied

It should look like:
```
Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjox...
```

### 5. Click the blue **Send** button

### 6. You'll see the WLC weights in the response:

```json
{
  "payload": {
    "rules": [
      { "key": "soil_ph", "weight": 0.08, ... },
      { "key": "soil_texture", "weight": 0.10, ... },
      { "key": "seasonal_rainfall", "weight": 0.15, ... },
      ...12 rules
    ]
  },
  "source": "database"
}
```

🎉 That's the validated reference-table data.

---

## 📸 Visual summary of what your Postman tabs should look like

**Tab 1 — Login:**
```
[POST ▼]  https://doing-haven-requisite.ngrok-free.dev/api/auth/login/   [Send]

Headers:
  ngrok-skip-browser-warning  →  true
  Content-Type                →  application/json

Body (raw, JSON):
  {
    "email": "your@email.com",
    "password": "yourpassword"
  }
```

**Tab 2 — Get WLC Rules:**
```
[GET ▼]  https://doing-haven-requisite.ngrok-free.dev/api/recommendations/rules/   [Send]

Headers:
  ngrok-skip-browser-warning  →  true
  Authorization               →  Bearer eyJhbGci...(paste full token here)
```

Do these in order — login first, copy token, then call the protected endpoint.

---

## ❗ If it doesn't work, check these 5 things:

| Problem | Fix |
|---|---|
| Empty response or HTML page | Add header `ngrok-skip-browser-warning: true` |
| `401 Unauthorized` | Token wrong → re-login and copy fresh token |
| `401 Unauthorized` after re-login | You forgot the word `Bearer ` before the token |
| `404 Not Found` | URL missing trailing slash `/` at the end |
| `405 Method Not Allowed` | Using wrong method (GET vs POST) |
| "Could not connect" / "tunnel offline" | Django + ngrok not running on your laptop |

---

# 2. How to register a new user

(Do this only if you don't have an account yet.)

**Method:** `POST`
**URL:**
```
https://doing-haven-requisite.ngrok-free.dev/api/auth/register/
```

**Headers:**
| KEY | VALUE |
|---|---|
| `ngrok-skip-browser-warning` | `true` |
| `Content-Type` | `application/json` |

**Body (raw → JSON):**
```json
{
  "email":        "panel.demo@georice.app",
  "password":     "Panel1234!",
  "password2":    "Panel1234!",
  "first_name":   "Panel",
  "last_name":    "Demo",
  "barangay":     "Tibungol",
  "municipality": "Panabo City",
  "province":     "Davao del Norte"
}
```

Click **Send** → if successful, go back to Section 1 and **log in**.

---

# 3. How to use the JWT token in other API calls

Once you have the `access_token` from login, add these 2 headers to **every** other API call:

| KEY | VALUE |
|---|---|
| `ngrok-skip-browser-warning` | `true` |
| `Authorization` | `Bearer <paste access_token here>` |

In Postman:
- Click the **Authorization** tab → Type: **Bearer Token** → paste the token in the right-side panel.
- OR add it manually in the **Headers** tab as shown above.

### Example: GET the WLC weights (your validated reference-table data)

**Method:** `GET`
**URL:**
```
https://doing-haven-requisite.ngrok-free.dev/api/recommendations/rules/
```

**Headers:**
| KEY | VALUE |
|---|---|
| `ngrok-skip-browser-warning` | `true` |
| `Authorization` | `Bearer eyJhbGciOiJIUzI1NiIs...` |

Click Send → returns the JSON with all 12 WLC weights + FAO ranges.

### Refreshing an expired token

If you get `401 Unauthorized`, your access token expired. Refresh it:

**Method:** `POST`
**URL:**
```
https://doing-haven-requisite.ngrok-free.dev/api/token/refresh/
```

**Body:**
```json
{ "refresh": "<paste your refresh_token here>" }
```

Returns a new `access_token`.

---

# 4. External APIs (no JWT required)

These are free public APIs the Django backend calls. You can paste these URLs directly into a browser tab to show panel real data.

---

## 🌍 SoilGrids — soil data

**What it gives us:** soil pH, texture, organic matter, drainage at a given lat/lng.

**Base URL:** `https://rest.isric.org/soilgrids/v2.0/properties/query`

**Example call (Panabo City coordinates):**
```
https://rest.isric.org/soilgrids/v2.0/properties/query?lon=125.6830&lat=7.3086&property=phh2o&property=clay&property=sand&property=silt&property=soc&depth=0-5cm&value=mean
```

**Authentication:** None. Open and free. **Paste this in a browser — it works immediately.**

**Where we call it from:** `apps/environmental/services/soilgrids.py`
**Where the result is used:** Fed into `environmental_scans` table → used by RSI scoring

---

## ☀️ Open-Meteo — current weather + forecast

**What it gives us:** current temperature, humidity, rainfall, weather code, wind speed.

**Base URL:** `https://api.open-meteo.com/v1/forecast`

**Example call (Panabo City):**
```
https://api.open-meteo.com/v1/forecast?latitude=7.3086&longitude=125.6830&current=temperature_2m,weather_code,precipitation,relative_humidity_2m,wind_speed_10m&hourly=temperature_2m,weather_code,precipitation,precipitation_probability&forecast_days=2&timezone=Asia/Manila
```

**Authentication:** None. Open and free.

**Where we call it from:** `apps/environmental/services/openmeteo.py`
**Where the result is used:** Saved into `environmental_scans` (avg_temperature, humidity, rainfall, etc.) → used by RSI scoring

---

## ⛰️ Open-Meteo — elevation

**What it gives us:** elevation in meters at a given lat/lng.

**Base URL:** `https://api.open-meteo.com/v1/elevation`

**Example call (Panabo City):**
```
https://api.open-meteo.com/v1/elevation?latitude=7.3086&longitude=125.6830
```

**Authentication:** None.

**Where we call it from:** `apps/environmental/services/openmeteo.py` → `get_elevation()`
**Where the result is used:** Saved as `farm.elevation_m` and `scan.elevation_m` → used by RSI scoring (elevation factor)

---

## 🗺️ OpenStreetMap Nominatim — reverse geocoding

**What it gives us:** human-readable address from lat/lng. RiceFlow no longer uses it for the
barangay (that comes from the official boundaries; see Farms).

**Base URL:** `https://nominatim.openstreetmap.org/reverse`

**Example call:**
```
https://nominatim.openstreetmap.org/reverse?format=json&lat=7.3086&lon=125.6830&zoom=18
```

**Authentication:** None, but they REQUIRE a `User-Agent` header. Without it you'll get "access denied" / 403.

**Where it's used:** Auto-fill farm address fields when the user pins on the map.

---

### ❌ Why you get "access denied" in Postman

OpenStreetMap Nominatim is run by volunteers. They **require every request to identify itself** with a `User-Agent` header that includes your app name + a contact email. If you don't send one, they block the request as "access denied".

- **Postman with no User-Agent** → blocked with 403 / "access denied"
- **A web browser** → works because the browser auto-adds its own User-Agent
- **Python `requests`** without specifying one → blocked

### ✅ The fix — add a User-Agent header

In Postman, add this header in the **Headers** tab:

| KEY | VALUE |
|---|---|
| `User-Agent` | `RiceFlow/1.0 (kurtlumpayao25@gmail.com)` |

(Put your real email so they can contact you if you accidentally hammer their server.)

Then try the URL again:
```
https://nominatim.openstreetmap.org/reverse?format=json&lat=7.3086&lon=125.6830&zoom=18
```

It will return JSON like:
```json
{
  "place_id": 12345,
  "lat": "7.3086",
  "lon": "125.6830",
  "display_name": "Tibungol, Panabo City, Davao del Norte, Philippines",
  "address": {
    "village":   "Tibungol",
    "town":      "Panabo City",
    "province":  "Davao del Norte",
    "country":   "Philippines"
  }
}
```

### 🚦 Other Nominatim rules to know (in case the panel asks)

1. **Max 1 request per second** — don't spam them
2. **User-Agent required** — must include app name + contact info
3. **For heavy use** → host your own Nominatim instance or use a paid alternative (MapBox, Google)
4. **Attribution required** — display "© OpenStreetMap contributors" somewhere in your app

### 🛡️ Easiest way to demo Nominatim

Use a **browser tab** instead of Postman — the browser sends a User-Agent automatically. Paste the URL into Chrome/Firefox and it just works. Save Postman for the protected backend endpoints.

---

# 5. Our backend APIs

⚠️ **Reminder:** Every URL below needs the `ngrok-skip-browser-warning: true` header and (except login/register) a `Bearer <token>` Authorization header.

**Replace `<TOKEN>` below with the access token you got from login.**

---

## 💓 Health check (public, no token)

```
GET https://doing-haven-requisite.ngrok-free.dev/api/health/
ngrok-skip-browser-warning: true
```

Response `200 OK` (or `503` if the database is down):
```json
{ "status": "ok", "database": "ok", "version": "<deployed git commit>" }
```

Used by the host and the CD pipeline to confirm a deploy is live. The admin-only `/api/auth/system-health/` still checks every external API.

---

## 🔐 Auth (`apps/users/`)

### Register a new user
```
POST https://doing-haven-requisite.ngrok-free.dev/api/auth/register/
Content-Type: application/json
ngrok-skip-browser-warning: true

{
  "email":        "juan@example.com",
  "password":     "strongpassword",
  "password2":    "strongpassword",
  "first_name":   "Juan",
  "last_name":    "Dela Cruz"
}
```
No barangay at sign-up: the farmer's barangay is taken from their first farm pin. City and
province are always Panabo City and Davao del Norte.

### Login
```
POST https://doing-haven-requisite.ngrok-free.dev/api/auth/login/
(See Section 1 above for full step-by-step)
```

### Forgot password
No token needed. Step 1 emails a 6-digit code to the account. The reply is the same whether or not
the email is registered.
```
POST /api/auth/password-reset/request/
{ "email": "juan@example.com" }

200 { "detail": "If that email is registered, a code is on its way." }
```

Step 2 sets the new password. A code lasts 10 minutes and 5 wrong tries, and only the newest code
works. An account gets at most one code a minute and 5 a day. Success logs the account out on
every device.
```
POST /api/auth/password-reset/confirm/
{ "email": "juan@example.com", "code": "123456", "new_password": "...", "new_password2": "..." }

200 { "detail": "Your password has been changed. You can log in now." }
400 { "code": ["That code is wrong or has expired. Please request a new one."] }
400 { "new_password": ["This password is too common."] }
```

### Get current user profile
```
GET https://doing-haven-requisite.ngrok-free.dev/api/auth/profile/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

### Refresh access token
```
POST https://doing-haven-requisite.ngrok-free.dev/api/token/refresh/
Content-Type: application/json
ngrok-skip-browser-warning: true

{ "refresh": "<refresh_token>" }
```

---

## 👥 Admin roles (admin website)

Two staff roles, from the flags already on the user (no extra table):

| Role | Flags | Can do |
|---|---|---|
| **Admin** (developers) | `is_staff` + `is_superuser` | Everything |
| **Validator** (agriculturist engineer) | `is_staff` only | Read the dashboard, farms, cycles, varieties, rules and yield models; correct a variety (`PUT`/`PATCH /api/varieties/<id>/`; `is_active` is ignored, so only the admin deactivates) |

Admin only (a validator gets `403`): `/api/auth/users/` (list, create, edit, delete),
`DELETE /api/farms/admin/<id>/`, `POST /api/farms/cleanup/`, `DELETE /api/progress/admin/cycles/<id>/`,
`POST /api/varieties/`, `DELETE /api/varieties/<id>/`, `POST /api/varieties/import-csv/`,
`PUT /api/recommendations/rules/`, both `train/` endpoints, and `set-model/`.

Farmer emails (`owner_email` in `/api/farms/all/` and `/api/progress/admin/cycles/`) are `null`
for a validator: contact details are for the admin only (Data Privacy Act).

### Season board (both roles)
```
GET /api/auth/admin-season/
Authorization: Bearer <TOKEN>
```
The dashboard's season board: active crops at each of the 10 growth stages (by the crop's age
or its logged steps), and four lists of farms that need attention. Each list has a `count` and
up to 8 `items`, worst first; rows carry `farm_id`, `farm`, `farmer` (name, no email), `barangay`.
```json
{
  "active_crops": 17,
  "stages": [{ "stage_no": 1, "name": "Germination & Seedling", "count": 4 }, …],
  "attention": {
    "late_steps":      { "count": 2, "items": [{ "step": "Level the field", "due": "2026-11-01", "days_late": 4, … }] },
    "problems":        { "count": 1, "items": [{ "issue": "pest", "issue_label": "Pest", "severity": "high", "date": "2026-11-04", "note": "…", … }] },
    "flagged_pins":    { "count": 3, "items": [{ "flag": "built_up", "kept": true, … }] },
    "harvest_overdue": { "count": 0, "items": [] }
  }
}
```
Late = the current PalayCheck step is 3+ days past its date. Problems = logs with an issue in the
last 7 days. Flagged pins = the location check said road, building, water or mangrove (`kept`:
the farmer kept the pin anyway). Overdue = 7+ days past the expected harvest with no yield record.

---

## 🌾 Farms (`apps/farms/`)

### List all my farms
```
GET https://doing-haven-requisite.ngrok-free.dev/api/farms/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

### Create a farm
```
POST https://doing-haven-requisite.ngrok-free.dev/api/farms/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
Content-Type: application/json

{
  "name":           "Santos Family Farm",
  "latitude":       7.3086,
  "longitude":      125.6830,
  "area_hectares":  2.5,
  "ecosystem":      "irrigated_lowland"
}
```
`barangay` is read-only: the server sets it from the pin using the official barangay boundaries
(NAMRIA v2023-11-06 + PSA PSGC, `apps/farms/land_data/panabo_barangays.geojson`), and again when
the pin moves. A pin between two barangays gets the nearest one. `GET /api/farms/check-location/`
returns the same `barangay` so the app can show it while the farmer moves the pin.
`python manage.py fix_farm_barangays` lists farms whose saved barangay differs from their pin
(`--apply` saves).

### Get one farm
```
GET https://doing-haven-requisite.ngrok-free.dev/api/farms/{farm_id}/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

---

## 🌱 Environmental Scan (`apps/environmental/`)

### Run a scan on a farm (calls SoilGrids + Open-Meteo)
```
POST https://doing-haven-requisite.ngrok-free.dev/api/environmental/scan/{farm_id}/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

**What this does:** The backend gets the farm's GPS coordinates, then **calls SoilGrids and Open-Meteo in parallel** using ThreadPoolExecutor. It saves the combined result as one row in `environmental_scans`. This is the data later used by RSI scoring.

**Soil texture from BSWM:** the texture comes from the **BSWM Philippine Soil Series** map at the pin (`soil_series`, e.g. "Cabangan clay loam" → `soil_texture` "clay loam"). It is a measured soil survey, so it replaces the SoilGrids texture, and it still works when SoilGrids is down. The map is clipped to Panabo City by `python manage.py load_soil_series --shapefile <PhilSoilSeries.shp>` into `apps/environmental/data/panabo_soil_series.geojson`. pH, organic matter and drainage still come from SoilGrids (or the defaults).

**Soil values from OpenLandMap first:** pH, organic carbon, clay, sand, silt and bulk density come from the **OpenLandMap-soildb** maps (2020-2022, 0-30 cm, 120 m, CC BY 4.0, [doi:10.5281/zenodo.15608972](https://doi.org/10.5281/zenodo.15608972)) saved for the Panabo area, so a scan reads them locally in about a second. SoilGrids is only the backup for a point outside that area. `soil_source` says which was used: `openlandmap`, `soilgrids`, or `default` (neither had values). The saved file `apps/environmental/data/panabo_openlandmap.npz` is not in git (`*.npz`), so build it once on each machine or server: `pip install rasterio` then `python manage.py load_openlandmap` (about a minute). Without it, scans use SoilGrids as before.

**When SoilGrids is slow or down:** a scan waits at most 20 s for soil, then uses the points that answered (or the defaults, `soil_sampling.estimated: true`); a slow point still finishes in the background and is cached for the next scan. After a failure SoilGrids is skipped for 10 minutes, so other scans do not wait on it. Only real SoilGrids values are cached (30 days), never defaults. A farm deleted while its scan runs gets `404`.

**Soil across the whole farm:** soil is read at the pin **plus points north, east, south and west of it**, spread over the farm's `area_hectares` (one point per 250 m SoilGrids pixel, so usually 1–5 points). The readings are averaged; points where SoilGrids has no data (built-up areas, water) are left out. Weather, rainfall and elevation are read at the pin, since their grids are bigger than a farm. The extra `soil_sampling` field reports what happened:

| Field | Meaning |
|---|---|
| `points` | soil points used in the average |
| `points_without_data` | points skipped because SoilGrids had no data there |
| `estimated` | `true` when no point had data, so the soil values are defaults |
| `ph_range`, `clay_pct_range` | lowest and highest reading across the points |
| `varies` | `true` when pH differs by more than 0.5 or clay by more than 10 points |
| `message` | when `varies`: advice to register the different parts of the land as separate farms |

**Response example:**
```json
{
  "id": 7,
  "farm": 1,
  "soil_ph": 6.2,
  "soil_texture": "clay loam",
  "soil_series": "Cabangan clay loam",
  "organic_matter": 2.5,
  "drainage": "poorly drained",
  "avg_temperature": 27,
  "seasonal_rainfall_mm": 1800,
  "humidity_pct": 82,
  "elevation_m": 45,
  "flood_risk": "Low",
  "soil_sampling": {
    "points": 3, "points_without_data": 0, "estimated": false,
    "ph_range": [5.2, 5.3], "clay_pct_range": [35.9, 37.4],
    "varies": false, "message": ""
  }
}
```

### Get scan history for a farm
```
GET https://doing-haven-requisite.ngrok-free.dev/api/environmental/history/{farm_id}/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

### Weather only (for the dashboard card)
```
GET https://doing-haven-requisite.ngrok-free.dev/api/environmental/weather/?lat=7.3086&lng=125.6830
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```
Besides `current` and the next 8 `hourly` entries, the response has `outlook` (used by the planting guide's weather advice) and `fetched_at` (when the server got the forecast; it is cached for 10 minutes):

```json
"outlook": {
  "rain_mm_6h": 0.0,  "rain_prob_6h": 20,
  "rain_mm_24h": 0.6, "rain_prob_24h": 88,
  "rain_mm_48h": 0.7, "rain_prob_48h": 88,
  "wind_kph_max_12h": 7
}
```

---

## ⭐ Recommendations & Rules (WLC) — `apps/recommendations/`

### ★ Get current WLC weights and FAO ranges
```
GET https://doing-haven-requisite.ngrok-free.dev/api/recommendations/rules/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

**This is the validated reference-table.csv data in JSON form.**
**Stored in:** `suitability_rule_set` table (Supabase Postgres), single row, `payload` JSON column.

**Response:**
```json
{
  "payload": {
    "rules": [
      { "key": "soil_ph",           "weight": 0.08, "type": "range",       "s1": {...}, "s2": {...}, "s3": {...} },
      { "key": "soil_texture",      "weight": 0.10, "type": "categorical", "options": [...] },
      { "key": "seasonal_rainfall", "weight": 0.15, "type": "threshold",   "s1": 1000, "s2": 700, "s3": 500 },
      ...12 rules total
    ]
  },
  "updated_at":      "2026-06-02T14:32:00Z",
  "updated_by_name": "admin",
  "source":          "database"
}
```

### Update WLC weights (admin only)
```
PUT https://doing-haven-requisite.ngrok-free.dev/api/recommendations/rules/
Authorization: Bearer <ADMIN_TOKEN>
ngrok-skip-browser-warning: true
Content-Type: application/json

{
  "payload": { "rules": [...] }
}
```

### Generate a recommendation (runs RSI for every variety)
```
POST https://doing-haven-requisite.ngrok-free.dev/api/recommendations/generate/{scan_id}/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

**Response example:**
```json
{
  "id": 12,
  "farm": 1,
  "scan": 7,
  "results": [
    {
      "rank": 1,
      "variety": { "nsic_code": "NSIC Rc160", "common_name": "Tubigan 14" },
      "rsi_score": 97.25,
      "suitability_class": "S1 - Highly Suitable",
      "factor_scores": { "soil_ph": 100, "soil_texture": 100, ... }
    },
    { "rank": 2, ... },
    { "rank": 3, ... }
  ]
}
```

### Get recommendation history for a farm
```
GET https://doing-haven-requisite.ngrok-free.dev/api/recommendations/history/{farm_id}/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

### Train K-means clustering models (admin only)
```
POST https://doing-haven-requisite.ngrok-free.dev/api/recommendations/train/
Authorization: Bearer <ADMIN_TOKEN>
ngrok-skip-browser-warning: true
```

### Set active clustering model (admin only)
```
POST https://doing-haven-requisite.ngrok-free.dev/api/recommendations/set-model/{model_name}/
Authorization: Bearer <ADMIN_TOKEN>
ngrok-skip-browser-warning: true
```
(model_name = `kmeans`, `agglomerative`, or `dbscan`)

---

## 🌾 Varieties (`apps/varieties/`)

### List all rice varieties (the dataset)
```
GET https://doing-haven-requisite.ngrok-free.dev/api/varieties/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

### Get one variety
```
GET https://doing-haven-requisite.ngrok-free.dev/api/varieties/{id}/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

---

## 📖 Planting Guides (`apps/guides/`)

### Get the PalayCheck planting guide
```
POST https://doing-haven-requisite.ngrok-free.dev/api/guides/generate/{recommendation_id}/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
Content-Type: application/json

{
  "variety":  12,
  "season":   "Wet Season",
  "language": "en"
}
```
The steps are a summary of the PalayCheck System 2022 Revised Edition (DA-PhilRice), timed for the variety's maturity (`apps/guides/palaycheck.py`). No AI writes them.

`variety` is optional: the id of the variety the farmer picked. It must be one of the recommendation's results (otherwise `400`). Without it the guide keeps the variety picked earlier for this farm, or else uses the top-ranked one.

`language` (`en`, `fil`, `ceb`) only changes the wording: the step ids and check-offs stay the same.

| `source` | Meaning |
|---|---|
| `PALAYCHECK` | the steps were just built (a new guide, a guide from before PalayCheck, or `"force_regenerate": true`) |
| `SAVED` | the saved steps, worded in the requested language |

`start_date` is the sowing day (day 0), 10 days after the guide is made, so the first step (seed preparation) is due the day the guide is made. Each step:

```json
{
  "id": 301, "stepNumber": 1, "key": "seeds", "keyCheck": 1,
  "title": "...", "instruction": "...", "explanation": "...",
  "reference": "PalayCheck 2022, pp. 14-15", "referenceUrl": "https://www.philrice.gov.ph/...pdf",
  "daysAfterPlanting": -10, "category": "planting", "is_completed": false
}
```

### List all guides
```
GET https://doing-haven-requisite.ngrok-free.dev/api/guides/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

### Mark a guide step as completed
```
PATCH https://doing-haven-requisite.ngrok-free.dev/api/guides/steps/{step_id}/complete/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

### Answer "Did you sow already?"
```
POST https://doing-haven-requisite.ngrok-free.dev/api/guides/{guide_id}/sowing/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
Content-Type: application/json

{ "sown": true, "date": "2026-11-12", "language": "en" }
```
- `"sown": true`: sown on `date` (default today; not in the future, at most 150 days ago). The guide's sowing day moves there, every step not done yet moves with it, the steps up to sowing count as done, a sowing log is saved, and the farm's active cycle gets that planting date and harvest date.
- `"sown": false`: not yet. Sowing moves 3 days later (from today or the planned day); `400` if sowing is already logged.

Returns the guide, like the generate endpoint. Logging the sowing step (`guide_step` = the "seedbed" step) does the same as `"sown": true` on the log date.

---

## 🤖 AI Chat (Gemini) — `apps/ai/`

### Send a chat message
```
POST https://doing-haven-requisite.ngrok-free.dev/api/ai/chat/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
Content-Type: application/json

{
  "message":  "How much fertilizer should I apply?",
  "history":  [],
  "language": "en",
  "farm":     12
}
```

`farm` is optional: the farm selected in the app. The answer uses that farm's scan, chosen
variety, crop day, field logs, the current PalayCheck guide step (its text and page, so the
answer follows the book; later steps are not sent, to save tokens) and weather. Another user's
farm is ignored (the newest of your own farms is used). `message` is at most 1000 characters.

**Response:**
```json
{
  "reply":    "Your Tubigan 18 is on day 28 (tillering), so apply about 1.5 bags of urea per hectare...",
  "language": "en",
  "grounded": true,
  "sources":  [{"title": "PalayCheck System for Irrigated Lowland Rice (2022 revised edition)",
                "publisher": "PhilRice", "pages": "p. 38", "url": "https://..."}]
}
```

**Booklet search (RAG).** With `GEMINI_FILE_SEARCH_STORE` set, GeoRice AI first searches the
DA-PhilRice booklets (PalayCheck 2022, Key Check 7, the field guide, the disease, snail and
pest handouts; `apps/ai/booklets.py`) with Gemini File Search, using the Flash-Lite models
that support it, and answers from what it finds. `sources` lists the booklet parts the
answer used (at most 4), with the printed page (`p. 48`), slide (`slide 15`) or `chart`;
`grounded` is `true` when there is at least one. If the search fails, the chat answers
without it (`grounded: false`, `sources: []`). A reply naming a pesticide is replaced by
advice to ask an agriculturist. The booklets are uploaded once with
`python manage.py load_booklets --dir <folder with the PDFs>`, which prints the store name
for `.env`; indexing costs about $0.02 and storage and search are free.

| Status | When |
|---|---|
| `400` | `message` is empty or longer than 1000 characters |
| `429` | the farmer reached `AI_CHAT_DAILY_LIMIT` answers today (default 15) |
| `503` | every Gemini model is out of free quota or busy; try again later |
| `504` | Gemini did not answer in time |

The same first question within 6 hours returns the saved answer and does not count toward the limit.

---

## 🗒️ Change log and farmer notices — `apps/activity/`

### Change log (admin only)
```
GET /api/activity/changes/?role=validator&limit=50
```
Every change made from the admin website, newest first: who (`actor_name`, `actor_role` =
`admin`/`validator`), what (`action`, `summary`, `target`), when (`created_at`), and the old and
new values (`changes`: `{"avg_yield_t_ha": [5.2, 5.4]}`). Passwords are never recorded, only
`"password": ["", "changed"]`. `role` and `limit` (default 100, max 500) are optional. Validators
and farmers get `403`.

Logged actions: accounts created, edited or deactivated; farms and cycles deleted; farm cleanup;
varieties added, edited, deactivated or imported; suitability rules saved; models retrained or
activated. An edit that changes nothing is not logged.

### Farmer notices (signed-in farmer)
```
GET /api/activity/notices/?after=<id>
```
The farmer's own notices from the last 30 days, newest first (at most 20); `after` returns only
newer ones. The app checks this when it opens and puts them in the bell.

| `kind` | When | `params` |
|---|---|---|
| `farm_removed` | the admin deleted their farm | `farm` |
| `cycle_removed` | the admin deleted their crop cycle | `farm`, `season`, `year` |
| `variety_updated` | a variety they are growing (active cycle) was edited | `variety` |
| `variety_retired` | a variety they are growing was deactivated | `variety` |

`title` and `body` are the English text; the app words the known kinds in the farmer's language.

---

## 🩺 Problem advice (booklets + AI) — `apps/advice/`

The advice for a field problem comes from official PhilRice / PalayCheck booklets
(`apps/advice/knowledge.py`): 9 problems plus "Not sure", every line in English,
Filipino and Bisaya with its booklet and page. The AI never adds advice: it matches the
farmer's words to a problem on the list, and explains that problem's cards for the farm.
Every AI point must name the cards it used; plain code rejects an answer that cites a card
it was not given, names a chemical or a dose, or brings in another problem. Then (or with
no AI at all) the farmer still gets the booklet card. Matching and explaining share the
farmer's daily AI limit with the chat (`AI_CHAT_DAILY_LIMIT`) and its `ai_chat` throttle.

### List the problems (for the picker)
```
GET https://doing-haven-requisite.ngrok-free.dev/api/advice/problems/?language=ceb
Authorization: Bearer <TOKEN>
```
`[{"key": "stem_borer", "category": "pest", "name": "Stem borer (aksip)", "hint": "..."}, ..., {"key": "unknown", ...}]`
Keys: `rats`, `stem_borer`, `black_bug`, `planthopper`, `golden_apple_snail`, `blast`,
`bacterial_leaf_blight`, `sheath_blight`, `tungro`, `unknown` (always last).

### The booklet card (no AI; always works)
```
GET https://doing-haven-requisite.ngrok-free.dev/api/advice/problems/stem_borer/?language=fil
Authorization: Bearer <TOKEN>
```
```json
{
  "key": "stem_borer", "category": "pest", "name": "Aksip (stem borer)",
  "identify":     [{"text": "...", "sources": [{"title": "Harmful Organisms in Philippine Rice Fields", "publisher": "PhilRice", "pages": "chart", "url": "..."}]}],
  "serious_when": {"text": "...", "sources": [{"title": "PalayCheck System ...", "pages": "p. 48", ...}]},
  "do_now":       [{"text": "...", "sources": [...]}],
  "dont":         [{"text": "...", "sources": [...]}],
  "next_season":  [{"text": "...", "sources": [...]}],
  "get_help":     {"text": "... text PhilRice at 0917-111-7423.", "sources": []},
  "urgent":       "Severe problem reported. ...",
  "checked_by_validator": false
}
```
`serious_when` is `null` for `unknown`. Show `urgent` when the farmer marks the problem as severe.

### Match the farmer's own words
```
POST https://doing-haven-requisite.ngrok-free.dev/api/advice/match/
Authorization: Bearer <TOKEN>
Content-Type: application/json

{ "text": "naay mga uhay nga puti ug walay sulod", "language": "ceb" }
```
`{"matches": [{"key": "stem_borer", "name": "Stem borer (aksip)", "why": "..."}], "ai_used": true}`
At most 3, best first, only keys from the list. Without the AI, the problem names and local
words in the text decide (`ai_used: false`, `why` empty); `matches` can be empty. The farmer
confirms one. `400` when `text` is empty.

### Explain a problem for this farm
```
POST https://doing-haven-requisite.ngrok-free.dev/api/advice/explain/
Authorization: Bearer <TOKEN>
Content-Type: application/json

{ "problem": "stem_borer", "language": "ceb", "farm": 12, "question": "Unsay akong buhaton karon?" }
```
`farm`, `question` and `log` are optional. The farm's stage, current guide step and weather
come from the same summary the chat uses. With `log` (the id of the farmer's own problem
log), the log's observation is the question, and a checked answer is saved on the log
(`advice_tip`): the problem card under the planting guide asks the AI only once per problem.
```json
{
  "problem": "stem_borer", "ai_used": true, "not_covered": false, "note": null,
  "points": [{"text": "Susiha ang imong uma sayo sa buntag ...", "cards": ["C4"],
              "sources": [{"title": "PalayCheck System ...", "pages": "p. 48", ...}]}]
}
```
With no checked answer, `points` is `[]`, `ai_used` is `false` and `note` says why:
`ai_unavailable`, `daily_limit` or `rejected`. Show the booklet card either way.
`400` for an unknown problem.

### Field logs name the problem
`POST /api/progress/logs/` takes an optional `problem_key` (a key from the list above).
It fills `issue_type` from the problem when that is empty; an unknown key is a `400`.
`PATCH /api/progress/logs/{id}/` with `{"resolved_at": "<ISO time>"}` marks the problem
fixed ("Okay na"): its card leaves the Guide tab and the admin season board. `advice_tip`
is read-only (written by the explain endpoint).

---

## 📊 Yield Prediction (Linear Regression) — `apps/predictions/`

### Predict yield from farm features
```
POST https://doing-haven-requisite.ngrok-free.dev/api/predictions/predict/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
Content-Type: application/json

{
  "area_ha":           2.5,
  "soil_ph":           6.2,
  "organic_matter":    2.5,
  "avg_temperature":   27,
  "seasonal_rainfall": 1800,
  "humidity":          82,
  "elevation_m":       45,
  "flood_risk":        "low",
  "ecosystem":         "irrigated_lowland",
  "maturity_days":     115,
  "variety_avg_yield": 6.0
}
```

**Response:**
```json
{
  "predicted_yield_t_ha": 6.42,
  "model_used":           "Linear Regression",
  "r2_score":             0.7321
}
```

Optional `farm_id`, `variety_id` and `cycle_id` fill in the farm's barangay and
ecosystem and the variety's seed type. With a `farm_id` (your own farm), the
prediction is also **saved** for that farm's newest crop (or `cycle_id`) as a
`YieldPrediction`, linked to the model that made it: one row per crop per model,
updated when asked again. Nothing is saved once the crop's harvest is recorded,
so every saved prediction can be compared fairly with the harvest.

### See every training (R², MAE, RMSE)
```
GET https://doing-haven-requisite.ngrok-free.dev/api/predictions/models/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```
Every training is kept, newest first; `is_active: true` marks the one in use.
`harvests_seen` is how many RiceFlow harvests that training learned from.

### Retrain now (admin only)
```
POST https://doing-haven-requisite.ngrok-free.dev/api/predictions/train/
Authorization: Bearer <ADMIN_TOKEN>
ngrok-skip-browser-warning: true
```
The new model is used from then on. Older trainings are kept (each with its own
model file) so saved predictions still point to the model that made them.

### Automatic retraining
After **5 new harvests** are recorded in RiceFlow (counted from the last training),
the model retrains in the background on all the data. The new model is used only if
its error on the DA test season is not worse than the current model's (MAE within 2%);
otherwise it is kept, inactive, with a note, and the current model stays in use. Each
automatic retrain is written to the change log as `model.auto_trained` by
`RiceFlow` (role `system`). The first model is always trained by the admin.

---

## 📈 Progress (cycles, logs, yield records) — `apps/progress/`

### List farm cycles for a farm
```
GET https://doing-haven-requisite.ngrok-free.dev/api/progress/cycles/?farm_id={farm_id}
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```
Each cycle has `stage` (`{"stage_no": 3, "name": "Tillering"}`): today's stage, from the days since sowing or the planting-guide steps logged, whichever is further along. `current_stage` is the stage saved when the cycle started.

### Create a farm cycle
```
POST https://doing-haven-requisite.ngrok-free.dev/api/progress/cycles/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```
A farm has one active cycle at a time: creating (or re-activating) a second one returns
`400 {"farm": [...]}`. Cycle responses include `variety_name` and `yield_per_ha`.

### Get one cycle
```
GET https://doing-haven-requisite.ngrok-free.dev/api/progress/cycles/{id}/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

### Update a cycle
```
PATCH https://doing-haven-requisite.ngrok-free.dev/api/progress/cycles/{id}/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

### List progress logs for a cycle
```
GET https://doing-haven-requisite.ngrok-free.dev/api/progress/logs/?cycle_id={cycle_id}
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

### Create a progress log
```
POST https://doing-haven-requisite.ngrok-free.dev/api/progress/logs/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
Content-Type: application/json

{
  "farm_cycle":   1,
  "log_date":     "2026-06-03",
  "growth_stage": 3,
  "issue_type":   "pest",
  "severity":     "low",
  "action_taken": "Sprayed pesticide",
  "observation":  "Saw a few stem borers",
  "guide_step":   301
}
```
- `guide_step` (optional) is the planting guide step this log finishes; saving the log marks that step done. It must be a step of the cycle's farm (otherwise `400`)
- Logging a step after sowing before sowing was logged returns `sowing_estimate` (the sowing day that step implies, e.g. transplanting minus 21 days) for the app to confirm
- `growth_stage` is a GrowthStage id from `GET /api/varieties/growth-stages/` (optional)
- `issue_type`: `pest`, `disease`, `weather`, `nutrient`, `other`, or `""` for none
- `severity`: `low`, `medium`, `high`, or `""`
- `observation` is required

### Get the yield record for a cycle
```
GET https://doing-haven-requisite.ngrok-free.dev/api/progress/cycles/{cycle_id}/yield/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

### Create/update a yield record
```
POST https://doing-haven-requisite.ngrok-free.dev/api/progress/cycles/{cycle_id}/yield/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
Content-Type: application/json

{
  "harvest_date":      "2026-09-15",
  "area_harvested_ha": 2.5,
  "gross_yield_kg":    7500,
  "net_yield_kg":      6800,
  "moisture_pct":      14.0
}
```
Creating the yield record (POST) marks the cycle `completed` and sets its
`actual_harvest_date`, so the farm's next recommendation starts a new cycle.
Just before saving, the yield model's prediction for the crop is saved (so the
harvest can be compared with it), and the 5th new harvest since the last training
starts an automatic retrain (see Yield Prediction).
Use PATCH on the same URL to correct a saved record.

---

# 6. Defense demo cheat sheet

## To show the panel where SoilGrids data comes from:
1. Open browser
2. Paste this URL:
   ```
   https://rest.isric.org/soilgrids/v2.0/properties/query?lon=125.6830&lat=7.3086&property=phh2o&depth=0-5cm&value=mean
   ```
3. Show them the JSON with the soil pH for Panabo

## To show the panel where the WLC weights live:
1. Get a JWT token via login (Section 1)
2. Open Postman
3. GET `https://doing-haven-requisite.ngrok-free.dev/api/recommendations/rules/` with:
   - `Authorization: Bearer <token>`
   - `ngrok-skip-browser-warning: true`
4. Show them the JSON `payload` field with all 12 weights and ranges

## To show the panel a live RSI calculation:
1. Use the same JWT token
2. POST `https://doing-haven-requisite.ngrok-free.dev/api/recommendations/generate/{scan_id}/`
3. Show them the response with `rsi_score: 97.25` and `factor_scores: {...}`

## To show the panel where data is stored:
1. Open Supabase Dashboard
2. Go to Table Editor
3. Click on `recommendations_suitabilityruleset` table
4. Click the single row's `payload` column to expand
5. Show them the JSON containing the validated FAO weights

---

# 7. Summary table — at a glance

| Source | URL | Auth | Used for |
|---|---|---|---|
| **SoilGrids** | rest.isric.org/soilgrids/v2.0 | None | soil pH, texture, drainage, OM |
| **Open-Meteo Forecast** | api.open-meteo.com/v1/forecast | None | temperature, humidity, rainfall |
| **Open-Meteo Elevation** | api.open-meteo.com/v1/elevation | None | elevation in meters |
| **Nominatim** | nominatim.openstreetmap.org | None | reverse geocoding |
| **Gemini** | generativelanguage.googleapis.com | API key (server-side) | AI chat |
| **Our backend** | doing-haven-requisite.ngrok-free.dev/api | JWT | everything else |
| **Health check** | /api/health/ | None | deploy and uptime checks |
| **WLC weights** | /api/recommendations/rules/ | JWT | the validated reference-table |
| **Recommendation** | /api/recommendations/generate/{scan_id}/ | JWT | runs RSI for all varieties |

---

# 8. Pre-defense checklist

- [ ] Start Django backend: `python manage.py runserver`
- [ ] Start ngrok tunnel (it must show `doing-haven-requisite.ngrok-free.dev`)
- [ ] Open Postman, set up the login request with **both required headers**
- [ ] Test login once → confirm you get an access_token
- [ ] Save the token in a Postman environment variable so you don't paste it manually each time
- [ ] Test one protected endpoint (e.g., GET `/api/recommendations/rules/`) → confirm it returns JSON
- [ ] Open Supabase dashboard in a browser tab, signed in
- [ ] Open the SoilGrids public URL in another tab → confirm it loads

**If all 8 boxes are checked, you can answer any "show me the data" question in 10 seconds.**

---

**Print this. Bring it to defense. You've got this.** 🌾
