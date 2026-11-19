# Homebound

A small macOS tool that sets **your own iPhone's** simulated GPS location from your Mac, using Apple's developer location-simulation service. No jailbreak, nothing installed on the phone.

Mode: **set-and-unplug**. With the default `devicectl` driver, a location set while plugged in stays after you unplug. It was tested on iOS 26.6.1; see [TEST_RESULTS.md](TEST_RESULTS.md).

## How it works

| Piece | What it does |
|---|---|
| **Pairing** | "Trust This Computer" creates keys that let this Mac talk to the phone. |
| **Developer Disk Image (DDI)** | A signed image the Mac mounts on the phone. It adds developer services, including location simulation. It is unmounted on every phone restart. |
| **Tunnel** | Since iOS 17, an encrypted link (over USB or Wi-Fi) that carries commands to those services. `devicectl` gets it from macOS. pymobiledevice3 builds its own and needs sudo. |
| **Location service** | Overrides what the phone's location system reports. Maps, Find My, and every other app see the simulated location. |

## Setup (one time)

1. **Xcode** installed and opened once. Check with `xcrun devicectl --version`.
2. **iPhone:** plug it in, unlock it, and tap **Trust**. Then turn on **Settings → Privacy & Security → Developer Mode** (the phone restarts; tap *Turn On*). If the toggle is missing, open Xcode → Window → Devices and Simulators with the phone plugged in.
3. **Start Homebound:**
   ```
   ./homebound.sh
   ```
   The first run creates `.venv` and installs the pinned `requirements.txt`. The app opens at <http://127.0.0.1:8765>.
4. Search for or click your dorm, type **Dorm** in the preset box, and click **Save**.

Optional fallback driver (pymobiledevice3, **tethered only**): in a separate Terminal window run
`sudo .venv/bin/pymobiledevice3 remote tunneld`, leave it open, and pick `pymobiledevice3` in the Driver menu. With this driver the location lasts only while Homebound runs and the phone stays plugged in.

## Before the trip (do these once)

- [ ] **Long hold:** set the Dorm preset, unplug, and check Apple Maps several hours later.
- [ ] **Friend check:** a friend who sees your location confirms Find My shows the dorm.
- [ ] **Restart check:** while it's set, restart the phone and confirm Maps shows your real location. That proves the emergency reset works.
- [ ] **Don't update iOS** before the trip. A new iOS version can need a new DDI and Xcode.

## Trip-day checklist (set-and-unplug)

At the dorm, before leaving:
1. Charge the phone. Pack the **Mac, its charger, and a phone cable**.
2. Plug in the iPhone, unlock it, and run `./homebound.sh`. The device panel should show every check green and **Ready**.
3. Click the **Dorm** preset, then **Set location**.
4. Open **Apple Maps** on the phone and tap the location arrow. When the blue dot is at the dorm, click **Yes, it's there**.
5. When the panel says **Safe to unplug**, unplug the phone. Check Maps once more after a minute.

During the trip:
- Check Maps occasionally. If the dot ever shows where you really are, plug in, unlock, and click **Re-apply Dorm**, then check Maps.
- **After any phone restart or dead battery**, the simulation is gone. Plug in and Re-apply **before** the phone gets a fix where you are. Turn on airplane mode first if you can, re-apply, and then turn it off.
- Flight: airplane mode is fine. Find My will show "Dorm · x hours ago", like any phone that's offline.

## Recovery: getting your real location back

1. **Restore real location** (big red button) with the phone plugged in and unlocked, or run:
   `xcrun devicectl device simulate location clear --device <UDID>`
2. If that fails or you don't have the Mac: **restart the iPhone**. That unmounts the DDI and always ends the simulation.

Then confirm in Apple Maps that the dot is at your real location.

## Troubleshooting

The device panel shows a fix for every failing check. The common ones:

| Problem | Fix |
|---|---|
| Connection: not connected | Plug in with a cable and unlock the phone. |
| Pairing | Unlock the phone and tap **Trust**. |
| Developer Mode off | Settings → Privacy & Security → Developer Mode. |
| DDI not mounted (normal right after a restart) | Wait about 30 s, unlocked and plugged in, then click Refresh. If it's still missing, run `.venv/bin/pymobiledevice3 mounter auto-mount`. |
| Address search finds nothing | Use the full name ("Powell Library, Los Angeles"), a street address, or paste `lat, lon`. |

## Development

```
.venv/bin/python -m pytest -q
```
Code layout:
- `homebound/drivers/`: the `set / clear / status` interface, with `devicectl` (the default) and `pymobiledevice3`
- `homebound/app.py`: the FastAPI app, bound to 127.0.0.1 only, which rejects requests from other websites
- `homebound/static/index.html`: the whole UI (Leaflet + OpenStreetMap)
- `data/`: presets, last-applied state, and the activity log (git-ignored)

Address search uses OpenStreetMap Nominatim, with at most 1 request per second and cached results.
