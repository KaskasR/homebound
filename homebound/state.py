"""Local storage: presets, last-applied location, and the activity log (all under data/)."""

from __future__ import annotations

import json
import threading
from collections import deque
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Store:
    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.dir = data_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.presets_path = self.dir / "presets.json"
        self.state_path = self.dir / "state.json"
        self.log_path = self.dir / "activity.log"
        self._lock = threading.Lock()
        self._log: deque[dict] = deque(maxlen=300)
        self._load_log_tail()

    # -- json helpers ----------------------------------------------------------
    def _read(self, path: Path, default):
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return default

    def _write(self, path: Path, data) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)  # atomic

    # -- presets ---------------------------------------------------------------
    def presets(self) -> list[dict]:
        return self._read(self.presets_path, [])

    def save_preset(self, name: str, lat: float, lon: float) -> list[dict]:
        with self._lock:
            presets = [p for p in self.presets() if p["name"].lower() != name.lower()]
            presets.append({"name": name, "lat": lat, "lon": lon})
            presets.sort(key=lambda p: p["name"].lower())
            self._write(self.presets_path, presets)
            return presets

    def delete_preset(self, name: str) -> list[dict]:
        with self._lock:
            presets = [p for p in self.presets() if p["name"] != name]
            self._write(self.presets_path, presets)
            return presets

    # -- last applied location ------------------------------------------------
    def state(self) -> dict:
        return self._read(self.state_path, {})

    def update_state(self, **changes) -> dict:
        with self._lock:
            st = self.state()
            st.update(changes)
            self._write(self.state_path, st)
            return st

    # -- activity log ------------------------------------------------------------
    def _load_log_tail(self) -> None:
        try:
            for line in self.log_path.read_text().splitlines()[-300:]:
                self._log.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass

    def log(self, level: str, message: str, fix: str = "") -> dict:
        entry = {"time": _now(), "level": level, "message": message, "fix": fix}
        with self._lock:
            self._log.append(entry)
            with self.log_path.open("a") as f:
                f.write(json.dumps(entry) + "\n")
        return entry

    def recent_log(self) -> list[dict]:
        return list(self._log)
