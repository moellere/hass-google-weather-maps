"""Web Mercator tile math. Pure functions, no Home Assistant imports."""

from __future__ import annotations

import math

from .const import MAP_TYPE_EU, MAP_TYPE_US

TILE_SIZE = 256


def lat_lon_to_tile(latitude: float, longitude: float, zoom: int) -> tuple[int, int, float, float]:
    """Return (tile_x, tile_y, frac_x, frac_y) for a location at a zoom level."""
    n = 2**zoom
    x = (longitude + 180.0) / 360.0 * n
    lat_rad = math.radians(latitude)
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    tile_x = min(n - 1, max(0, int(x)))
    tile_y = min(n - 1, max(0, int(y)))
    return tile_x, tile_y, x - tile_x, y - tile_y


def tile_grid(latitude: float, longitude: float, zoom: int, grid_size: int) -> list[list[tuple[int, int]]]:
    """Return a grid_size x grid_size grid of (x, y) tiles around a location.

    The grid is chosen so the location sits as close to the center as
    possible: 1x1 is the containing tile, 2x2 picks the quadrant neighbors,
    3x3 surrounds the containing tile. X wraps around the antimeridian;
    Y is clamped to the map edge.
    """
    n = 2**zoom
    tile_x, tile_y, frac_x, frac_y = lat_lon_to_tile(latitude, longitude, zoom)
    if grid_size == 1:
        x_start, y_start = tile_x, tile_y
    elif grid_size == 2:
        x_start = tile_x - 1 if frac_x < 0.5 else tile_x
        y_start = tile_y - 1 if frac_y < 0.5 else tile_y
    else:
        x_start, y_start = tile_x - 1, tile_y - 1
    y_start = min(max(y_start, 0), max(0, n - grid_size))
    return [
        [((x_start + col) % n, y_start + row) for col in range(grid_size)]
        for row in range(grid_size)
    ]


def resolve_map_type(latitude: float, longitude: float) -> str | None:
    """Pick the covering precipitation map type for a location, if any."""
    if 14.0 <= latitude <= 72.0 and -180.0 <= longitude <= -50.0:
        return MAP_TYPE_US
    if 29.0 <= latitude <= 72.0 and -32.0 <= longitude <= 45.0:
        return MAP_TYPE_EU
    return None


def marker_pixel(
    latitude: float, longitude: float, zoom: int, grid: list[list[tuple[int, int]]]
) -> tuple[float, float]:
    """Return the pixel position of a location within a stitched tile grid."""
    n = 2**zoom
    x_start, y_start = grid[0][0]
    tile_x, tile_y, frac_x, frac_y = lat_lon_to_tile(latitude, longitude, zoom)
    col = (tile_x - x_start) % n
    row = tile_y - y_start
    return ((col + frac_x) * TILE_SIZE, (row + frac_y) * TILE_SIZE)
