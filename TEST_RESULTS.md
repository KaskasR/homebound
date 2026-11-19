# Homebound: Persistence Test Results

## Environment (2026-11-19)
- Mac: macOS 27.0.1 (arm64), Xcode 27.2, devicectl 651.32
- Python 3.13.15, pymobiledevice3 11.60.0 (project venv)
- iPhone 16 (iPhone17,3), iOS 26.6.1, UDID 00000000-0000000000000000
- Developer Mode: on. Personalized DDI: mounted (version 651.32)

## Test coordinate
- devicectl: Powell Library, UCLA: 34.07161, -118.44219
- pymobiledevice3: Pauley Pavilion, UCLA: 34.07043, -118.44686 (different spot so a stale dot can't fool us)

## Driver 1: devicectl
| Check | Time | Result |
|---|---|---|
| Set, blue dot moved in Maps | 04:03:47 set; 04:05 checked | ✅ Dot at Powell Library. Command exits after ~26 s; location held after exit while plugged in |
| Unplugged +1 min | unplugged 04:06:59 | Not reported separately (held at +5) |
| Unplugged +5 min | 04:12 | ✅ Still at Powell |
| Unplugged +30 min | | ⏭️ Skipped for now (user chose to move on) |
| Friend confirms in Find My | ~04:13 | ✅ (partial) Find My on user's own Mac (iCloud server-side location) shows phone at Powell. Friend check from separate account still pending |
| Clear restores real location | 04:15:37 | ✅ Maps and Find My (Mac) both back to real location. Clear took ~1 s |

## Driver 2: pymobiledevice3
| Check | Time | Result |
|---|---|---|
| Set, blue dot moved in Maps | 04:17:51 set; ~04:18 checked | ✅ Dot at Pauley Pavilion. Via `sudo pymobiledevice3 remote tunneld` + `developer dvt simulate-location set --tunnel <UDID>`; process stays open, prints nothing while active |
| Ctrl+C (session ended), still plugged in | SIGINT 04:18:32 | ❌ Dot returned to real location as soon as the session ended |
| Unplugged +1 min | | N/A: unplugging ends the session, which already reverts the location |
| Unplugged +5 min | | N/A: unplugging ends the session, which already reverts the location |
| Unplugged +30 min | | N/A: unplugging ends the session, which already reverts the location |
| Clear restores real location | | N/A: ending the session restored it automatically |

## Notes
- pymobiledevice3: simulation is tied to the open `set` session. Location reverts when the process exits.
- devicectl: negative longitude must use `--longitude=-118.44219` (the `=` form); otherwise it is parsed as a flag.
- devicectl `coordinate` returns and exits; it does not hold a session open. Simulation persisted after the process ended (phone still plugged in).

## Conclusion (2026-11-19)
- **devicectl**: location persists after the command exits AND after unplugging (verified to +5 min), and it shows in Find My (iCloud). Set-and-unplug mode is viable.
- **pymobiledevice3**: tethered only. Needs sudo tunneld plus a live session; reverts when the session ends.
- **Still to verify before the trip**: a multi-hour unplugged hold, a friend's Find My check from a separate account, and that a phone restart clears simulation.
