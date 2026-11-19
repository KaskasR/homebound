#!/bin/sh
# Build Homebound.app into ~/Applications (shows up in Launchpad and Spotlight).
# Re-run this if you move the repo folder.
set -eu
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-$HOME/Applications}"
APP="$DEST/Homebound.app"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$DEST"
sed "s|@@REPO@@|$REPO|g" "$REPO/scripts/Homebound.applescript" > "$TMP/Homebound.applescript"
rm -rf "$APP"
osacompile -s -o "$APP" "$TMP/Homebound.applescript"   # -s = stay-open applet

# Icon
if [ ! -f "$REPO/assets/icon.png" ]; then
  swift "$REPO/scripts/make-icon.swift" "$REPO/assets/icon.png"
fi
ICONSET="$TMP/Homebound.iconset"; mkdir -p "$ICONSET"
for s in 16 32 128 256 512; do
  sips -z $s $s "$REPO/assets/icon.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  d=$((s * 2)); sips -z $d $d "$REPO/assets/icon.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/applet.icns"
# macOS prefers the asset-catalog icon (Assets.car via CFBundleIconName) over applet.icns,
# so remove it, or the Dock shows the generic script icon.
rm -f "$APP/Contents/Resources/Assets.car"
/usr/libexec/PlistBuddy -c "Delete :CFBundleIconName" "$APP/Contents/Info.plist" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier local.homebound.app" "$APP/Contents/Info.plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string local.homebound.app" "$APP/Contents/Info.plist"
codesign --force --deep -s - "$APP" 2>/dev/null  # re-sign ad hoc after editing Info.plist
touch "$APP"
# Tell Launch Services about the new icon.
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP" >/dev/null 2>&1 || true
echo "Built $APP"
