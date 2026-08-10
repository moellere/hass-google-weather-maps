# Google Weather Maps for Home Assistant

A custom integration that renders Google's experimental
[weather map tiles](https://developers.google.com/maps/documentation/weather/weather-map)
(US / EU precipitation nowcast) as a Home Assistant **camera entity** — a
radar-style image you can put in a picture card, dashboard, or notification.

Companion to the official
[`google_weather`](https://www.home-assistant.io/integrations/google_weather/)
core integration (same Google Maps Platform API key), deliberately under its
own domain so it never shadows the core integration. Background and design
rationale: [homelab-helper proposal](https://github.com/moellere/homelab-helper/blob/main/docs/google-weather-ha-integration-proposal.md).

## What you get

- `camera.<name>_precipitation_map` — an N×N tile grid centered on your
  location, stitched into one PNG, refreshed on an interval you choose.
- Map type auto-selected (`US_PRECIPITATION_CURRENT` / `EU_PRECIPITATION_CURRENT`)
  from the configured coordinates, with a manual override.
- The API key stays server-side — tiles are proxied through Home Assistant,
  never exposed to the frontend as raw Google URLs.
- Multiple entries supported (different locations, zooms, or regions).

Note: Google currently serves only a "current" frame per tile — there is no
timestamped history, so no animated radar loop yet.

## Installation

### HACS (custom repository)

1. HACS → three-dot menu → **Custom repositories**.
2. Repository: `moellere/hass-google-weather-maps`, type: **Integration**.
3. Install **Google Weather Maps**, restart Home Assistant.

### Manual

Copy `custom_components/google_weather_maps/` into your `config/custom_components/`
directory and restart.

## Configuration

Settings → Devices & services → **Add integration** → *Google Weather Maps*.

| Field | Notes |
|---|---|
| API key | Google Maps Platform key with the **Weather API** enabled |
| Latitude / longitude | Defaults to your Home Assistant home location |
| Map type | `Auto` picks US/EU from the location |

Options (per entry): zoom level (0–16, default 7), tile grid size (1×1 to
3×3, default 2×2), refresh interval (default 15 min).

## Quota and cost

Every tile in the grid is one Weather API call per refresh. Defaults
(2×2 @ 15 min) are ~11,700 calls/month — the API's free tier is 10,000
calls/month ($0.15/1,000 beyond), *shared* with the `google_weather`
integration if you use the same key (~4,400 calls/month/location). Widen the
refresh interval or drop to 1×1 if you need to stay inside the free tier.
Tile-endpoint SKU pricing is not yet published; treat the numbers above as
the conservative estimate.

## Caveats

- The weather map endpoint is **Experimental (pre-GA)**: Google may change
  or remove it without notice.
- Google's documentation demonstrates these tiles overlaid on Google Maps;
  displaying them standalone may sit in a gray area of the Maps Platform
  terms of service. Review the ToS for your use case.
- Coverage is US and EU only (as of the current map type list).
