#!/bin/zsh
APP_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$APP_DIR" || exit 1
if [ ! -x "$APP_DIR/SFP Seri Numaraları.app/Contents/MacOS/SFPLauncher" ]; then
  /bin/zsh "$APP_DIR/Mac_Uygulama_Olustur.command" || exit 1
fi
exec /usr/bin/open "$APP_DIR/SFP Seri Numaraları.app"
