"""FastAPI backend. Bound to 127.0.0.1 only (see __main__)."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .drivers import DEFAULT_DRIVER, DRIVERS, DriverError, LocationDriver
from .geocode import Geocoder, parse_latlon
from .state import Store

STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Homebound")
store = Store()
geocoder = Geocoder()
_drivers: dict[str, LocationDriver] = {}
_device_lock = asyncio.Lock()  # one phone command at a time


def current_driver_name() -> str:
    name = store.state().get("driver", DEFAULT_DRIVER)
    return name if name in DRIVERS else DEFAULT_DRIVER


def driver() -> LocationDriver:
    name = current_driver_name()
    if name not in _drivers:
        _drivers[name] = DRIVERS[name]()
    return _drivers[name]


def fail(e: DriverError) -> JSONResponse:
    store.log("error", e.message, e.fix)
    return JSONResponse({"ok": False, "error": e.message, "fix": e.fix}, status_code=409)


class Coord(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    label: str = ""


class Preset(Coord):
    name: str = Field(min_length=1, max_length=60)


class DriverChoice(BaseModel):
    driver: str


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/api/status")
async def status():
    async with _device_lock:
        st = await asyncio.to_thread(driver().status)
    return {"device": st.to_dict(), "state": store.state(), "drivers": list(DRIVERS)}


@app.post("/api/driver")
def choose_driver(body: DriverChoice):
    if body.driver not in DRIVERS:
        raise HTTPException(400, f"Unknown driver {body.driver}")
    store.update_state(driver=body.driver)
    store.log("info", f"Driver switched to {body.driver}")
    return {"ok": True}


async def _apply(lat: float, lon: float, label: str, action: str):
    try:
        async with _device_lock:
            msg = await asyncio.to_thread(driver().set, lat, lon)
    except DriverError as e:
        return fail(e)
    st = store.update_state(active=True, lat=lat, lon=lon, label=label, driver=current_driver_name(),
                            applied_at=datetime.now().isoformat(timespec="seconds"), verified_in_maps=False)
    store.log("ok", f"{action}: {label + ' – ' if label else ''}{msg}")
    return {"ok": True, "message": msg, "state": st}


@app.post("/api/set")
async def set_location(body: Coord):
    return await _apply(body.lat, body.lon, body.label, "Set")


@app.post("/api/reapply")
async def reapply():
    st = store.state()
    if "lat" not in st:
        return fail(DriverError("Nothing to re-apply yet.", "Pick a location on the map and click Set location first."))
    return await _apply(st["lat"], st["lon"], st.get("label", ""), "Re-applied")


@app.post("/api/confirm")
def confirm_in_maps():
    st = store.update_state(verified_in_maps=True)
    store.log("ok", "You confirmed the blue dot in Apple Maps. Safe to unplug.")
    return {"ok": True, "state": st}


@app.post("/api/clear")
async def clear():
    try:
        async with _device_lock:
            msg = await asyncio.to_thread(driver().clear)
    except DriverError as e:
        return fail(e)
    st = store.update_state(active=False, verified_in_maps=False,
                            cleared_at=datetime.now().isoformat(timespec="seconds"))
    store.log("ok", msg)
    return {"ok": True, "message": msg, "state": st}


@app.get("/api/presets")
def list_presets():
    return store.presets()


@app.post("/api/presets")
def save_preset(body: Preset):
    presets = store.save_preset(body.name.strip(), body.lat, body.lon)
    store.log("info", f"Saved preset '{body.name.strip()}' ({body.lat:.6f}, {body.lon:.6f})")
    return presets


@app.delete("/api/presets/{name}")
def delete_preset(name: str):
    store.log("info", f"Deleted preset '{name}'")
    return store.delete_preset(name)


@app.get("/api/search")
async def search(q: str):
    coord = parse_latlon(q)
    if coord:
        return [{"name": f"{coord[0]:.6f}, {coord[1]:.6f}", "lat": coord[0], "lon": coord[1]}]
    try:
        return await geocoder.search(q)
    except httpx.HTTPError as e:
        store.log("error", f"Address search failed: {e}", "Check your internet connection, or paste 'lat, lon' instead.")
        raise HTTPException(502, "Address search failed. Check your internet, or paste 'lat, lon'.")


@app.get("/api/log")
def log():
    return store.recent_log()
