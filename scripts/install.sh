#!/bin/sh
# Build the .ipk and install it on a rooted LG TV through the Homebrew Channel's
# telnet root shell (port 23). The package is sent as base64 over the same
# connection, so the TV never has to reach back to this machine and SSH is not
# needed.
#
# Usage: scripts/install.sh <tv-ip>      (or set TV_IP)
set -eu
TV="${1:-${TV_IP:-}}"
[ -n "$TV" ] || { echo "usage: $0 <tv-ip>   (or set TV_IP)" >&2; exit 2; }
cd "$(dirname "$0")/.."
ID=$(python3 -c 'import json; print(json.load(open("app/appinfo.json"))["id"])')

IPK=$(python3 scripts/build-ipk.py)
echo "Built $IPK"

python3 scripts/tvshell.py "$TV" --put "$IPK" "/tmp/$ID.ipk" >/dev/null
RESULT=$(python3 scripts/tvshell.py "$TV" "timeout 90 luna-send -i luna://com.webos.appInstallService/dev/install \
  '{\"id\":\"$ID\",\"ipkUrl\":\"/tmp/$ID.ipk\",\"subscribe\":true}' 2>&1 \
  | grep -m1 -oE '\"state\":\"(installed|install failed)\"|errorText\":\"[^\"]*'; rm -f /tmp/$ID.ipk")
echo "$RESULT"
case "$RESULT" in *'"installed"'*) ;; *) echo "Install did not report success" >&2; exit 1 ;; esac

echo "Launch it: python3 scripts/tvshell.py $TV \"luna-send -n 1 luna://com.webos.applicationManager/launch '{\\\"id\\\":\\\"$ID\\\"}'\""
