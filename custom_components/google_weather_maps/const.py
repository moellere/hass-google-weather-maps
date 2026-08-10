"""Constants for the Google Weather Maps integration."""

from typing import Final

DOMAIN: Final = "google_weather_maps"

CONF_MAP_TYPE: Final = "map_type"
CONF_ZOOM: Final = "zoom"
CONF_GRID_SIZE: Final = "grid_size"
CONF_UPDATE_INTERVAL: Final = "update_interval"

MAP_TYPE_AUTO: Final = "auto"
MAP_TYPE_US: Final = "US_PRECIPITATION_CURRENT"
MAP_TYPE_EU: Final = "EU_PRECIPITATION_CURRENT"

DEFAULT_ZOOM: Final = 7
DEFAULT_GRID_SIZE: Final = 2
DEFAULT_UPDATE_INTERVAL_MINUTES: Final = 15

MIN_ZOOM: Final = 0
MAX_ZOOM: Final = 16

TILE_URL: Final = (
    "https://weather.googleapis.com/v1/mapTypes/{map_type}/mapTiles/{zoom}/{x}/{y}"
)
ATTRIBUTION: Final = "Weather map data by Google"
