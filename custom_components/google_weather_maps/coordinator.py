"""Coordinator that fetches and stitches Google weather map tiles."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from http import HTTPStatus
import io
import logging

import aiohttp
from PIL import Image, ImageDraw, ImageEnhance

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .basemap import BasemapClient, BasemapError
from .const import (
    BASEMAP_BRIGHTNESS,
    CONF_BASEMAP,
    CONF_GRID_SIZE,
    CONF_MAP_TYPE,
    CONF_UPDATE_INTERVAL,
    CONF_ZOOM,
    DEFAULT_BASEMAP,
    DEFAULT_GRID_SIZE,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DEFAULT_ZOOM,
    DOMAIN,
    MAP_TYPE_AUTO,
    TILE_URL,
)
from .tiles import TILE_SIZE, marker_pixel, resolve_map_type, tile_grid

_LOGGER = logging.getLogger(__name__)

type GoogleWeatherMapsConfigEntry = ConfigEntry[GoogleWeatherMapsCoordinator]


async def async_fetch_tile(
    session: aiohttp.ClientSession, api_key: str, map_type: str, zoom: int, x: int, y: int
) -> bytes:
    """Fetch a single weather map tile."""
    url = TILE_URL.format(map_type=map_type, zoom=zoom, x=x, y=y)
    async with session.get(url, params={"key": api_key}) as resp:
        if resp.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise ConfigEntryAuthFailed(f"Tile request rejected: HTTP {resp.status}")
        if resp.status != HTTPStatus.OK:
            body = await resp.text()
            raise UpdateFailed(f"Tile request failed: HTTP {resp.status}: {body[:200]}")
        return await resp.read()


BACKGROUND_COLOR = (17, 24, 39, 255)
MARKER_COLOR = (239, 68, 68, 255)


def _paste_grid(tiles: list[list[bytes]], size: int) -> Image.Image:
    """Paste a grid of tile images onto one RGBA canvas."""
    canvas = Image.new("RGBA", (size, size))
    for row_index, row in enumerate(tiles):
        for col_index, tile_bytes in enumerate(row):
            tile = Image.open(io.BytesIO(tile_bytes)).convert("RGBA")
            canvas.paste(tile, (col_index * TILE_SIZE, row_index * TILE_SIZE))
    return canvas


def _stitch(
    tiles: list[list[bytes]],
    grid_size: int,
    marker: tuple[float, float],
    basemap_tiles: list[list[bytes]] | None,
) -> bytes:
    """Combine tile grids into one PNG. Blocking; run in executor.

    The precipitation tiles are transparent overlays, so they are composited
    onto the dimmed basemap when one is available (dark background otherwise);
    the configured location is drawn as a marker for orientation.
    """
    size = TILE_SIZE * grid_size
    overlay = _paste_grid(tiles, size)
    if basemap_tiles is not None:
        base = _paste_grid(basemap_tiles, size)
        base = ImageEnhance.Brightness(base).enhance(BASEMAP_BRIGHTNESS)
        base.putalpha(255)
    else:
        base = Image.new("RGBA", (size, size), BACKGROUND_COLOR)
    canvas = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(canvas)
    marker_x, marker_y = int(marker[0]), int(marker[1])
    draw.ellipse(
        (marker_x - 7, marker_y - 7, marker_x + 7, marker_y + 7),
        outline=MARKER_COLOR,
        width=2,
    )
    draw.ellipse((marker_x - 2, marker_y - 2, marker_x + 2, marker_y + 2), fill=MARKER_COLOR)
    out = io.BytesIO()
    canvas.convert("RGB").save(out, format="PNG")
    return out.getvalue()


class GoogleWeatherMapsCoordinator(DataUpdateCoordinator[bytes]):
    """Fetch the tile grid on an interval and keep the stitched PNG."""

    config_entry: GoogleWeatherMapsConfigEntry

    def __init__(self, hass: HomeAssistant, entry: GoogleWeatherMapsConfigEntry) -> None:
        """Initialize the coordinator from entry data and options."""
        options = entry.options
        interval = options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(minutes=interval),
        )
        self._session = async_get_clientsession(hass)
        self._api_key: str = entry.data[CONF_API_KEY]
        self._latitude: float = entry.data[CONF_LATITUDE]
        self._longitude: float = entry.data[CONF_LONGITUDE]
        self._basemap: BasemapClient | None = (
            BasemapClient(self._session, self._api_key)
            if options.get(CONF_BASEMAP, DEFAULT_BASEMAP)
            else None
        )
        self._basemap_warned = False
        self.zoom: int = options.get(CONF_ZOOM, DEFAULT_ZOOM)
        self.grid_size: int = options.get(CONF_GRID_SIZE, DEFAULT_GRID_SIZE)
        map_type: str = entry.data.get(CONF_MAP_TYPE, MAP_TYPE_AUTO)
        if map_type == MAP_TYPE_AUTO:
            resolved = resolve_map_type(self._latitude, self._longitude)
            if resolved is None:
                raise ConfigEntryError("Location is outside US/EU map coverage")
            map_type = resolved
        self.map_type = map_type

    async def _async_update_data(self) -> bytes:
        """Fetch all tiles in the grid and stitch them."""
        grid = tile_grid(self._latitude, self._longitude, self.zoom, self.grid_size)
        try:
            rows = [
                await asyncio.gather(
                    *(
                        async_fetch_tile(
                            self._session, self._api_key, self.map_type, self.zoom, x, y
                        )
                        for x, y in row
                    )
                )
                for row in grid
            ]
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching weather map tiles: {err}") from err
        basemap_rows = await self._async_basemap_rows(grid)
        marker = marker_pixel(self._latitude, self._longitude, self.zoom, grid)
        return await self.hass.async_add_executor_job(
            _stitch, rows, self.grid_size, marker, basemap_rows
        )

    async def _async_basemap_rows(
        self, grid: list[list[tuple[int, int]]]
    ) -> list[list[bytes]] | None:
        """Fetch basemap tiles for the grid; None disables the basemap layer."""
        if self._basemap is None:
            return None
        try:
            rows = [
                await asyncio.gather(
                    *(self._basemap.async_get_tile(self.zoom, x, y) for x, y in row)
                )
                for row in grid
            ]
        except BasemapError as err:
            if not self._basemap_warned:
                self._basemap_warned = True
                _LOGGER.warning(
                    "Basemap unavailable, falling back to plain background"
                    " (is the Map Tiles API enabled for this key?): %s",
                    err,
                )
            return None
        self._basemap_warned = False
        return rows
