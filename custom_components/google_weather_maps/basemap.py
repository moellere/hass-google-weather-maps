"""Google Map Tiles API client for the basemap layer.

Basemap tiles for an entry are a small fixed set at a fixed zoom, so they are
cached in memory for the life of the coordinator: the Map Tiles API is only
hit on startup, reload, or session-token renewal.
"""

from __future__ import annotations

from http import HTTPStatus
import logging

import aiohttp

from .const import BASEMAP_SESSION_URL, BASEMAP_TILE_URL

_LOGGER = logging.getLogger(__name__)


class BasemapError(Exception):
    """Raised when a basemap tile cannot be fetched."""


class BasemapClient:
    """Fetch and cache Google 2D map tiles behind a session token."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str) -> None:
        """Initialize the client."""
        self._session = session
        self._api_key = api_key
        self._token: str | None = None
        self._cache: dict[tuple[int, int, int], bytes] = {}

    async def _async_create_session(self) -> str:
        """Create a Map Tiles API session token."""
        try:
            async with self._session.post(
                BASEMAP_SESSION_URL,
                params={"key": self._api_key},
                json={"mapType": "roadmap", "language": "en-US", "region": "US"},
            ) as resp:
                data = await resp.json()
                if resp.status != HTTPStatus.OK:
                    message = data.get("error", {}).get("message", f"HTTP {resp.status}")
                    raise BasemapError(f"Map Tiles session rejected: {message}")
                token: str = data["session"]
        except aiohttp.ClientError as err:
            raise BasemapError(f"Map Tiles session request failed: {err}") from err
        return token

    async def _async_fetch(self, zoom: int, x: int, y: int, token: str) -> aiohttp.ClientResponse:
        """Perform one tile GET with a session token."""
        return await self._session.get(
            BASEMAP_TILE_URL.format(zoom=zoom, x=x, y=y),
            params={"key": self._api_key, "session": token},
        )

    async def async_get_tile(self, zoom: int, x: int, y: int) -> bytes:
        """Return a basemap tile, from cache when possible."""
        key = (zoom, x, y)
        if key in self._cache:
            return self._cache[key]
        if self._token is None:
            self._token = await self._async_create_session()
        try:
            resp = await self._async_fetch(zoom, x, y, self._token)
            if resp.status != HTTPStatus.OK:
                resp.release()
                _LOGGER.debug(
                    "Basemap tile %s returned HTTP %s; renewing session token",
                    key,
                    resp.status,
                )
                self._token = await self._async_create_session()
                resp = await self._async_fetch(zoom, x, y, self._token)
            if resp.status != HTTPStatus.OK:
                body = await resp.text()
                raise BasemapError(
                    f"Basemap tile failed: HTTP {resp.status}: {body[:200]}"
                )
            tile = await resp.read()
        except aiohttp.ClientError as err:
            raise BasemapError(f"Error fetching basemap tile: {err}") from err
        self._cache[key] = tile
        return tile
