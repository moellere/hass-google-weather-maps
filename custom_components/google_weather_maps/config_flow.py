"""Config flow for the Google Weather Maps integration."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
)
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
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
    MAP_TYPE_EU,
    MAP_TYPE_US,
    MAX_ZOOM,
    MIN_ZOOM,
)
from .coordinator import async_fetch_tile
from .tiles import lat_lon_to_tile, resolve_map_type

_MAP_TYPE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[MAP_TYPE_AUTO, MAP_TYPE_US, MAP_TYPE_EU],
        translation_key="map_type",
    )
)


class GoogleWeatherMapsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup of a weather map."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the API key, location, and map type."""
        errors: dict[str, str] = {}
        if user_input is not None:
            latitude: float = user_input[CONF_LATITUDE]
            longitude: float = user_input[CONF_LONGITUDE]
            map_type: str = user_input[CONF_MAP_TYPE]
            if map_type == MAP_TYPE_AUTO:
                resolved = resolve_map_type(latitude, longitude)
                if resolved is None:
                    errors["base"] = "not_covered"
                else:
                    map_type = resolved
            if not errors:
                await self.async_set_unique_id(
                    f"{latitude:.4f}_{longitude:.4f}_{map_type}"
                )
                self._abort_if_unique_id_configured()
                tile_x, tile_y, _, _ = lat_lon_to_tile(
                    latitude, longitude, DEFAULT_ZOOM
                )
                try:
                    await async_fetch_tile(
                        async_get_clientsession(self.hass),
                        user_input[CONF_API_KEY],
                        map_type,
                        DEFAULT_ZOOM,
                        tile_x,
                        tile_y,
                    )
                except ConfigEntryAuthFailed:
                    errors["base"] = "invalid_auth"
                except (UpdateFailed, aiohttp.ClientError, TimeoutError):
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title=f"Weather map {latitude:.2f}, {longitude:.2f}",
                        data={
                            CONF_API_KEY: user_input[CONF_API_KEY],
                            CONF_LATITUDE: latitude,
                            CONF_LONGITUDE: longitude,
                            CONF_MAP_TYPE: map_type,
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Required(
                    CONF_LATITUDE, default=self.hass.config.latitude
                ): vol.Coerce(float),
                vol.Required(
                    CONF_LONGITUDE, default=self.hass.config.longitude
                ): vol.Coerce(float),
                vol.Required(CONF_MAP_TYPE, default=MAP_TYPE_AUTO): _MAP_TYPE_SELECTOR,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow."""
        return GoogleWeatherMapsOptionsFlow()


class GoogleWeatherMapsOptionsFlow(OptionsFlow):
    """Tune zoom, grid size, and refresh interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and save the options."""
        if user_input is not None:
            user_input[CONF_ZOOM] = int(user_input[CONF_ZOOM])
            user_input[CONF_GRID_SIZE] = int(user_input[CONF_GRID_SIZE])
            user_input[CONF_UPDATE_INTERVAL] = int(user_input[CONF_UPDATE_INTERVAL])
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ZOOM, default=options.get(CONF_ZOOM, DEFAULT_ZOOM)
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_ZOOM, max=MAX_ZOOM, mode=NumberSelectorMode.SLIDER
                    )
                ),
                vol.Required(
                    CONF_GRID_SIZE,
                    default=options.get(CONF_GRID_SIZE, DEFAULT_GRID_SIZE),
                ): NumberSelector(
                    NumberSelectorConfig(min=1, max=3, mode=NumberSelectorMode.SLIDER)
                ),
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=options.get(
                        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5,
                        max=180,
                        step=5,
                        mode=NumberSelectorMode.SLIDER,
                        unit_of_measurement="min",
                    )
                ),
                vol.Required(
                    CONF_BASEMAP,
                    default=options.get(CONF_BASEMAP, DEFAULT_BASEMAP),
                ): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
