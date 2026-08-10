"""Camera entity serving the stitched Google weather map."""

from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import GoogleWeatherMapsConfigEntry, GoogleWeatherMapsCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GoogleWeatherMapsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the weather map camera for a config entry."""
    async_add_entities([GoogleWeatherMapCamera(entry.runtime_data)])


class GoogleWeatherMapCamera(
    CoordinatorEntity[GoogleWeatherMapsCoordinator], Camera
):
    """Precipitation nowcast map as a camera image."""

    _attr_has_entity_name = True
    _attr_translation_key = "precipitation_map"
    _attr_attribution = ATTRIBUTION
    content_type = "image/png"

    def __init__(self, coordinator: GoogleWeatherMapsCoordinator) -> None:
        """Initialize the camera."""
        super().__init__(coordinator)
        Camera.__init__(self)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}-map"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Google",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def extra_state_attributes(self) -> dict[str, str | int]:
        """Expose the map type, zoom and grid used to build the image."""
        return {
            "map_type": self.coordinator.map_type,
            "zoom": self.coordinator.zoom,
            "grid_size": self.coordinator.grid_size,
        }

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the current stitched map image."""
        return self.coordinator.data
