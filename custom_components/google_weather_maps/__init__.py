"""The Google Weather Maps integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import GoogleWeatherMapsConfigEntry, GoogleWeatherMapsCoordinator

_PLATFORMS: list[Platform] = [Platform.CAMERA]


async def async_setup_entry(
    hass: HomeAssistant, entry: GoogleWeatherMapsConfigEntry
) -> bool:
    """Set up Google Weather Maps from a config entry."""
    coordinator = GoogleWeatherMapsCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: GoogleWeatherMapsConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)


async def _async_update_options(
    hass: HomeAssistant, entry: GoogleWeatherMapsConfigEntry
) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
