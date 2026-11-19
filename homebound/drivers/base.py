"""The small interface every location driver implements: set / clear / status."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Protocol


class DriverError(Exception):
    """A failure with a plain-English fix the UI can show."""

    def __init__(self, message: str, fix: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.fix = fix


@dataclass
class Check:
    """One line in the device panel, e.g. 'Developer Mode: on'."""

    name: str
    ok: bool
    detail: str
    fix: str = ""


@dataclass
class DeviceStatus:
    driver: str
    ready: bool  # True when set() is expected to work right now
    connected: bool
    device_name: str = ""
    model: str = ""
    ios_version: str = ""
    udid: str = ""
    checks: list[Check] = field(default_factory=list)
    # Does a set location survive unplugging / the app quitting?
    persists_after_unplug: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class LocationDriver(Protocol):
    name: str

    def status(self) -> DeviceStatus: ...

    def set(self, lat: float, lon: float) -> str: ...

    def clear(self) -> str: ...


def validate_coordinate(lat: float, lon: float) -> None:
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise DriverError(
            f"Invalid coordinate {lat}, {lon}.",
            "Latitude must be between -90 and 90, longitude between -180 and 180.",
        )
