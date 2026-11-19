# Homebound: Persistence Test Results

## Environment (2026-11-19)
- Mac: macOS 27.0.1 (arm64), Xcode 27.2, devicectl 651.32
- Python 3.13.15, pymobiledevice3 11.60.0 (project venv)
- iPhone 16 (iPhone17,3), iOS 26.6.1, UDID 00000000-0000000000000000
- Developer Mode: on. Personalized DDI: mounted (version 651.32)

## Test coordinate
Powell Library, UCLA: 34.07161, -118.44219 (on campus, not far away)

## Driver 1: devicectl
| Check | Time | Result |
|---|---|---|
| Set, blue dot moved in Maps | 04:03:47 set; 04:05 checked | ✅ Dot at Powell Library. Command exits after ~26 s; location held after exit while plugged in |
| Unplugged +1 min | unplugged 04:06:59 | Not reported separately (held at +5) |
| Unplugged +5 min | 04:12 | ✅ Still at Powell |
| Unplugged +30 min | | ⏭️ Skipped for now (user chose to move on) |
| Friend confirms in Find My | ~04:13 | ✅ (partial) Find My on user's own Mac (iCloud server-side location) shows phone at Powell. Friend check from separate account still pending |
| Clear restores real location | | |

## Driver 2: pymobiledevice3
| Check | Time | Result |
|---|---|---|
| Set, blue dot moved in Maps | | |
| Ctrl+C (session ended), still plugged in | | |
| Unplugged +1 min | | |
| Unplugged +5 min | | |
| Unplugged +30 min | | |
| Clear restores real location | | |

## Notes
- devicectl: negative longitude must use `--longitude=-118.44219` (the `=` form); otherwise it is parsed as a flag.
- devicectl `coordinate` returns and exits; it does not hold a session open. Simulation persisted after the process ended (phone still plugged in).
