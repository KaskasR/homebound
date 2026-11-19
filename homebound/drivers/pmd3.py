"""Driver using pymobiledevice3 (fallback; TETHERED ONLY).

Tested on iOS 26.6.1: the simulated location lasts only while the `set` session is
open. Quitting Homebound or unplugging the phone ends the session and the phone
returns to its real location. Requires `sudo pymobiledevice3 remote tunneld`
running in another Terminal window.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from .base import Check, DeviceStatus, DriverError, validate_coordinate

TUNNELD_URL = "http://127.0.0.1:49151/"
PMD3 = str(Path(sys.executable).with_name("pymobiledevice3"))
FIX_TUNNELD = (
    "Open a new Terminal window, run this, and leave it open:\n"
    f"sudo {PMD3} remote tunneld"
)
FIX_PLUG_IN = "Plug the iPhone into this Mac with a cable and unlock it."


class Pymobiledevice3Driver:
    name = "pymobiledevice3"

    def __init__(self, udid: str | None = None, tunneld_url: str = TUNNELD_URL) -> None:
        self.udid = udid
        self.tunneld_url = tunneld_url
        self._session: subprocess.Popen | None = None

    def _tunnels(self) -> dict:
        try:
            with urllib.request.urlopen(self.tunneld_url, timeout=3) as r:
                return json.load(r)
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            raise DriverError(f"tunneld isn't running ({e}).", FIX_TUNNELD)

    def _session_alive(self) -> bool:
        return self._session is not None and self._session.poll() is None

    def status(self) -> DeviceStatus:
        st = DeviceStatus(driver=self.name, ready=False, connected=False, persists_after_unplug=False)
        try:
            tunnels = self._tunnels()
        except DriverError as e:
            st.checks.append(Check("Tunnel (tunneld)", False, e.message, e.fix))
            return st
        st.checks.append(Check("Tunnel (tunneld)", True, "tunneld is running"))
        udids = [u for u in tunnels if not self.udid or u == self.udid]
        if not udids:
            st.checks.append(Check("iPhone", False, "tunneld has no tunnel to an iPhone", FIX_PLUG_IN))
            return st
        st.udid = udids[0]
        st.connected = True
        st.checks.append(Check("Connection", True, "Tunnel up"))
        st.checks.append(Check("Session", self._session_alive(),
                               "Simulation session running" if self._session_alive() else "No active session",
                               "" if self._session_alive() else "Click Set location to start one."))
        st.ready = True
        return st

    def set(self, lat: float, lon: float) -> str:
        validate_coordinate(lat, lon)
        st = self.status()
        if not st.ready:
            bad = next(c for c in st.checks if not c.ok)
            raise DriverError(f"{bad.name}: {bad.detail}", bad.fix)
        self._stop_session()
        cmd = [PMD3, "developer", "dvt", "simulate-location", "set", "--tunnel", st.udid,
               "--", f"{lat:.6f}", f"{lon:.6f}"]
        self._session = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        time.sleep(4)  # give it time to fail fast if it's going to
        if not self._session_alive():
            out = (self._session.stdout.read() if self._session.stdout else "").strip()
            raise DriverError(f"pymobiledevice3 exited: {out.splitlines()[-1] if out else 'no output'}",
                              "Check the tunneld window for errors, unlock the phone, and try again.")
        return (f"Location set to {lat:.6f}, {lon:.6f} via pymobiledevice3 "
                "(holds only while Homebound runs and the phone stays plugged in)")

    def _stop_session(self) -> None:
        if self._session_alive():
            self._session.send_signal(2)  # SIGINT, like Ctrl+C
            try:
                self._session.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._session.kill()
        self._session = None

    def clear(self) -> str:
        self._stop_session()
        st = self.status()
        if st.ready:
            subprocess.run([PMD3, "developer", "dvt", "simulate-location", "clear", "--tunnel", st.udid],
                           capture_output=True, text=True, timeout=30)
        return "Simulation session ended (phone is using real GPS again)"
