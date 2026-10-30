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

**What it gives us:** human-readable address from lat/lng (e.g., barangay name).

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
  "last_name":    "Dela Cruz",
  "barangay":     "Tibungol",
  "municipality": "Panabo City",
  "province":     "Davao del Norte"
}
```

### Login
```
POST https://doing-haven-requisite.ngrok-free.dev/api/auth/login/
(See Section 1 above for full step-by-step)
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
  "barangay":       "Tibungol",
  "latitude":       7.3086,
  "longitude":      125.6830,
  "area_hectares":  2.5,
  "ecosystem":      "irrigated_lowland"
}
```

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

### Generate a planting guide using Gemini
```
POST https://doing-haven-requisite.ngrok-free.dev/api/guides/generate/{recommendation_id}/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
Content-Type: application/json

{
  "variety":  12,
  "season":   "Wet Season",
  "language": "en",
  "logs":     []
}
```
`variety` is optional: the id of the variety the farmer picked. It must be one of the recommendation's results (otherwise `400`). Without it the guide keeps the variety picked earlier for this farm, or else uses the top-ranked one.

### Append one new step to a guide
```
POST https://doing-haven-requisite.ngrok-free.dev/api/guides/append-step/{recommendation_id}/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
Content-Type: application/json

{
  "category":       "fertilizer",
  "last_day":       20,
  "existing_count": 8,
  "variety":        12,
  "language":       "en",
  "logs":           []
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
variety, crop day, field logs, next guide steps and weather. Another user's farm is ignored
(the newest of your own farms is used). `message` is at most 1000 characters.

**Response:**
```json
{
  "reply":    "Your Tubigan 18 is on day 28 (tillering), so apply about 1.5 bags of urea per hectare...",
  "language": "en"
}
```

| Status | When |
|---|---|
| `400` | `message` is empty or longer than 1000 characters |
| `429` | the farmer reached `AI_CHAT_DAILY_LIMIT` answers today (default 15) |
| `503` | every Gemini model is out of free quota or busy; try again later |
| `504` | Gemini did not answer in time |

The same first question within 6 hours returns the saved answer and does not count toward the limit.

### AI knowledge sheet (admins only)
```
GET https://doing-haven-requisite.ngrok-free.dev/api/ai/knowledge/
PUT https://doing-haven-requisite.ngrok-free.dev/api/ai/knowledge/
Authorization: Bearer <ADMIN_TOKEN>
ngrok-skip-browser-warning: true
Content-Type: application/json

{
  "content": "Topdress urea at early tillering, about 21 days after transplanting. (Source: PhilRice PalayCheck)"
}
```

The rice-farming reference the AI chat answers from, written by agriculturists from PhilRice
and DA sources (each part names its source). It goes into every chat, so it is capped at
`max_chars` (20,000, about 10 pages). Empty means the chat uses general knowledge. Farmers
get `403`. Also editable in Django admin under **AI knowledge sheet**.

**Response:**
```json
{
  "content":         "Topdress urea at early tillering ... (Source: PhilRice PalayCheck)",
  "updated_at":      "2026-10-30T15:20:00+08:00",
  "updated_by_name": "agri@georice.app",
  "max_chars":       20000
}
```

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

### See all trained model stats (R², MAE, RMSE)
```
GET https://doing-haven-requisite.ngrok-free.dev/api/predictions/models/
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

### Retrain all models (admin only)
```
POST https://doing-haven-requisite.ngrok-free.dev/api/predictions/train/
Authorization: Bearer <ADMIN_TOKEN>
ngrok-skip-browser-warning: true
```

---

## 📈 Progress (cycles, logs, yield records) — `apps/progress/`

### List farm cycles for a farm
```
GET https://doing-haven-requisite.ngrok-free.dev/api/progress/cycles/?farm_id={farm_id}
Authorization: Bearer <TOKEN>
ngrok-skip-browser-warning: true
```

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
  "observation":  "Saw a few stem borers"
}
```
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
| **Gemini** | generativelanguage.googleapis.com | API key (server-side) | AI chat + planting guide |
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
