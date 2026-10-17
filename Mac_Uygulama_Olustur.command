#!/bin/zsh
set -e
SFP_PROJECT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
SFP_BUNDLE="$SFP_PROJECT_DIR/SFP Seri Numaraları.app"
mkdir -p "$SFP_BUNDLE/Contents/MacOS" "$SFP_PROJECT_DIR/.build/swift-cache"
cp "$SFP_PROJECT_DIR/desktop/Info.plist" "$SFP_BUNDLE/Contents/Info.plist"
/usr/bin/xcrun swiftc "$SFP_PROJECT_DIR/desktop/macos.swift" \
  -swift-version 5 -O -framework Cocoa -framework WebKit \
  -target "$(uname -m)-apple-macos13.0" \
  -module-cache-path "$SFP_PROJECT_DIR/.build/swift-cache" \
  -o "$SFP_BUNDLE/Contents/MacOS/SFPLauncher"
/usr/bin/xattr -dr com.apple.FinderInfo "$SFP_BUNDLE" 2>/dev/null || true
/usr/bin/xattr -dr com.apple.ResourceFork "$SFP_BUNDLE" 2>/dev/null || true
/usr/bin/codesign --force --sign - "$SFP_BUNDLE"
echo "Hazır: $SFP_BUNDLE"
