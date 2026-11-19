"""Driver using Apple's `xcrun devicectl` (default; tested to persist after unplug)."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from typing import Callable

from .base import Check, DeviceStatus, DriverError, validate_coordinate

Runner = Callable[..., subprocess.CompletedProcess]

FIX_PLUG_IN = "Plug the iPhone into this Mac with a cable and unlock it."
FIX_TRUST = "Unlock the iPhone. If it asks 'Trust This Computer?', tap Trust and enter your passcode."
FIX_DEVMODE = (
    "On the iPhone: Settings → Privacy & Security → Developer Mode → On. "
    "The phone restarts; after unlocking, tap 'Turn On'."
)
FIX_DDI = (
    "The Developer Disk Image isn't mounted yet (normal right after a restart). "
    "Keep the phone unlocked and plugged in and wait ~30 s, then Refresh. If it stays like this, run: "
    ".venv/bin/pymobiledevice3 mounter auto-mount"
)
FIX_XCODE = "Install Xcode from the App Store, open it once, then run: xcode-select -s /Applications/Xcode.app"


class DevicectlDriver:
    name = "devicectl"

    def __init__(self, udid: str | None = None, runner: Runner = subprocess.run, timeout: int = 60) -> None:
        self.udid = udid
        self._run = runner
        self.timeout = timeout

    # -- helpers -----------------------------------------------------------
    def _devicectl(self, *args: str) -> dict:
        """Run devicectl with JSON output written to a temp file and return the parsed JSON."""
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            cmd = ["xcrun", "devicectl", *args, "--timeout", str(self.timeout), "--json-output", path]
            try:
                proc = self._run(cmd, capture_output=True, text=True, timeout=self.timeout + 15)
            except FileNotFoundError:
                raise DriverError("xcrun/devicectl not found.", FIX_XCODE)
            except subprocess.TimeoutExpired:
                raise DriverError("devicectl timed out talking to the iPhone.", FIX_PLUG_IN)
            try:
                with open(path) as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                data = {}
            if proc.returncode != 0:
                raise self._explain_failure(proc.stderr or proc.stdout or "", data)
            return data
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    @staticmethod
    def _explain_failure(text: str, data: dict) -> DriverError:
        err = data.get("error") or {}
        lines = text.strip().splitlines()
        try:
            msg = err["userInfo"]["NSLocalizedDescription"]["string"]
        except (KeyError, TypeError):
            msg = lines[-1] if lines else "devicectl failed with no message"
        low = (text + json.dumps(err)).lower()
        if "usage assertion" in low:  # CoreDevice error 4016: device not reachable
            return DriverError("The iPhone isn't reachable from this Mac.", FIX_PLUG_IN)
        if "developer mode" in low:
            return DriverError(msg, FIX_DEVMODE)
        if "locked" in low or "passcode" in low:
            return DriverError(msg, "Unlock the iPhone and keep it unlocked, then try again.")
        if "pair" in low or "trust" in low:
            return DriverError(msg, FIX_TRUST)
        if "disk image" in low or "ddi" in low:
            return DriverError(msg, FIX_DDI)
        if "not found" in low or "unavailable" in low or "no device" in low or "not connected" in low:
            return DriverError(msg, FIX_PLUG_IN)
        return DriverError(msg, "Unplug and replug the iPhone, unlock it, and try again.")

    def _find_iphone(self) -> dict | None:
        data = self._devicectl("list", "devices")
        devices = data.get("result", {}).get("devices", [])
        phones = [d for d in devices if d.get("hardwareProperties", {}).get("deviceType") == "iPhone"
                  and d.get("hardwareProperties", {}).get("reality", "physical") == "physical"]
        if self.udid:
            phones = [d for d in phones if d.get("hardwareProperties", {}).get("udid") == self.udid]
        # Prefer the one that's actually connected.
        phones.sort(key=lambda d: d.get("connectionProperties", {}).get("tunnelState") != "connected")
        return phones[0] if phones else None

    # -- interface ---------------------------------------------------------
    def status(self) -> DeviceStatus:
        st = DeviceStatus(driver=self.name, ready=False, connected=False, persists_after_unplug=True)
        try:
            dev = self._find_iphone()
        except DriverError as e:
            st.checks.append(Check("devicectl", False, e.message, e.fix))
            return st
        st.checks.append(Check("devicectl", True, "Xcode's devicectl is available"))
        if not dev:
            st.checks.append(Check("iPhone", False, "No iPhone known to this Mac", FIX_PLUG_IN))
            return st

        hw, dp, cp = dev.get("hardwareProperties", {}), dev.get("deviceProperties", {}), dev.get("connectionProperties", {})
        st.device_name = dp.get("name", "")
        st.model = hw.get("marketingName") or hw.get("productType", "")
        st.ios_version = dp.get("osVersionNumber", "")
        st.udid = hw.get("udid", "")
        if not self.udid:
            self.udid = st.udid

        paired = cp.get("pairingState") == "paired"
        st.checks.append(Check("Pairing", paired, "Paired with this Mac" if paired else f"Not paired ({cp.get('pairingState', 'unknown')})",
                               "" if paired else FIX_TRUST))

        st.connected = cp.get("tunnelState") == "connected"
        transport = cp.get("transportType", "")
        st.checks.append(Check("Connection", st.connected,
                               f"Connected ({transport})" if st.connected else "Not connected",
                               "" if st.connected else FIX_PLUG_IN))
        if not st.connected:
            # Developer Mode / DDI fields aren't reported while disconnected.
            return st

        devmode = dp.get("developerModeStatus") == "enabled"
        st.checks.append(Check("Developer Mode", devmode, "On" if devmode else "Off", "" if devmode else FIX_DEVMODE))

        ddi = bool(dp.get("ddiServicesAvailable"))
        st.checks.append(Check("Developer Disk Image", ddi, "Mounted" if ddi else "Not mounted", "" if ddi else FIX_DDI))

        st.ready = paired and st.connected and devmode and ddi
        return st

    def _require_device(self) -> str:
        st = self.status()
        if not st.ready:
            bad = next((c for c in st.checks if not c.ok), None)
            raise DriverError(f"iPhone not ready: {bad.name} – {bad.detail}" if bad else "iPhone not ready.",
                              bad.fix if bad else FIX_PLUG_IN)
        return st.udid

    def set(self, lat: float, lon: float) -> str:
        validate_coordinate(lat, lon)
        udid = self._require_device()
        # `=` form is required: a bare negative longitude is parsed as a flag.
        self._devicectl("device", "simulate", "location", "coordinate", "--device", udid,
                        f"--latitude={lat:.6f}", f"--longitude={lon:.6f}")
        return f"Location set to {lat:.6f}, {lon:.6f} via devicectl"

    def clear(self) -> str:
        udid = self._require_device()
        self._devicectl("device", "simulate", "location", "clear", "--device", udid)
        return "Location simulation cleared (phone is using real GPS again)"
