"""Address search via OpenStreetMap Nominatim, following its usage policy:
an identifying User-Agent, at most 1 request per second, and caching of results."""

from __future__ import annotations

import asyncio
import re
import time

import httpx

from . import __version__

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = f"Homebound/{__version__} (personal single-user desktop tool)"
LATLON_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*$")


def parse_latlon(text: str) -> tuple[float, float] | None:
    """Parse '34.0716, -118.4422' (or space-separated). Returns None if not a coordinate."""
    m = LATLON_RE.match(text)
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return lat, lon
    return None


class Geocoder:
    def __init__(self, min_interval: float = 1.0) -> None:
        self.min_interval = min_interval
        self._lock = asyncio.Lock()
        self._last = 0.0
        self._cache: dict[str, list[dict]] = {}

    async def search(self, query: str) -> list[dict]:
        key = query.strip().lower()
        if not key:
            return []
        if key in self._cache:
            return self._cache[key]
        async with self._lock:  # serialize requests so we never exceed 1/sec
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, timeout=10) as client:
                    r = await client.get(NOMINATIM_URL, params={"q": query, "format": "jsonv2", "limit": 5})
            finally:
                self._last = time.monotonic()
            r.raise_for_status()
            results = [{"name": item["display_name"], "lat": float(item["lat"]), "lon": float(item["lon"])}
                       for item in r.json()]
            self._cache[key] = results
            return results
