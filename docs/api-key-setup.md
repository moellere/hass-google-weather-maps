# Generating a Google Maps Platform API key for the Weather API

The integration needs a Google Maps Platform API key with the **Weather API**
enabled. The same key works for the official `google_weather` core
integration, so you only need to do this once.

## 1. Create (or pick) a Google Cloud project

1. Go to the [Google Cloud console](https://console.cloud.google.com/).
2. Create a new project (or reuse an existing one dedicated to home
   automation — a separate project keeps quota and billing visibility clean).
3. A **billing account must be attached** to the project. The Weather API has
   a free tier (10,000 calls/month), but Google Maps Platform APIs refuse
   requests from projects without billing enabled.

## 2. Enable the Weather API

1. Open [APIs & Services → Library](https://console.cloud.google.com/apis/library)
   and search for **Weather API**, or go directly to
   <https://console.cloud.google.com/apis/library/weather.googleapis.com>.
2. Click **Enable**.

Note: the weather map tiles and minute forecast endpoints are
**Experimental (pre-GA)** features of the Weather API — no separate
enablement is needed, but coverage is US/EU (tiles) and populated areas
(minute forecast).

## 3. Create the API key

1. Open [APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials).
2. **Create credentials → API key.** Copy the key.

## 4. Restrict the key (strongly recommended)

Edit the key and set:

- **API restrictions** → *Restrict key* → select only **Weather API**.
  A leaked key then can't be abused against Maps, Places, etc.
- **Application restrictions**: use **None** or **IP addresses** (your home's
  public IP, if reasonably static). Do **not** use *Websites* (HTTP referrer)
  restriction — this integration calls the API from the Home Assistant
  backend without a browser referrer, so a referrer-restricted key will be
  rejected with 403.

## 5. Cap your spend

Two guardrails, either or both:

- **Quota cap:** [APIs & Services → Weather API → Quotas](https://console.cloud.google.com/apis/api/weather.googleapis.com/quotas)
  — cap requests/day so a misconfiguration can't run past the free tier
  (10,000 calls/month ≈ 330/day).
- **Budget alert:** Billing → Budgets & alerts → create a small budget
  (even $1) with email alerts.

Quota context for this integration: each camera refresh fetches one API call
per tile — the default 2×2 grid at 15 minutes is ~11,700 calls/month, and the
core `google_weather` integration adds ~4,400/month per location on the same
key. Stretch the refresh interval or use a 1×1 grid to stay inside the free
tier. Tile-endpoint SKU pricing is not yet published; assume $0.15/1,000
beyond the free tier as the conservative estimate.

## 6. Use the key

Settings → Devices & services → **Add integration** → *Google Weather Maps*
→ paste the key. The config flow validates it by fetching one real tile
before creating the entry, so a bad key fails immediately with a clear error.
