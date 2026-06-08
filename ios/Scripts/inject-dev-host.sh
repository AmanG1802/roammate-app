#!/bin/bash
#
# Inject the dev Mac's current LAN IP into the built app's Info.plist as
# `DevLANHost`, so Config.swift can reach the backend from a physical device
# without anyone hand-editing an IP. Runs as a post-build phase (after the
# Info.plist is in the bundle, before code signing).
#
# Only relevant for Debug builds onto a physical device:
#   - Simulator builds use localhost and ignore DevLANHost.
#   - Release builds use the production URL and never read DevLANHost.
#
set -euo pipefail

[ "${CONFIGURATION:-}" = "Debug" ]   || { echo "inject-dev-host: not Debug, skipping"; exit 0; }
[ "${PLATFORM_NAME:-}" = "iphoneos" ] || { echo "inject-dev-host: not a device build, skipping"; exit 0; }

# Find the LAN IP of the active interface. Wi-Fi/Ethernet vary across Macs,
# so probe the common ones, then fall back to the default route's interface.
detect_ip() {
    local ifc ip def
    for ifc in en0 en1 en2; do
        ip=$(ipconfig getifaddr "$ifc" 2>/dev/null) || true
        if [ -n "${ip:-}" ]; then echo "$ip"; return 0; fi
    done
    def=$(route -n get default 2>/dev/null | awk '/interface:/{print $2}') || true
    if [ -n "${def:-}" ]; then
        ipconfig getifaddr "$def" 2>/dev/null || true
    fi
}

IP="$(detect_ip)"
if [ -z "${IP:-}" ]; then
    echo "warning: inject-dev-host could not detect a LAN IP; leaving DevLANHost untouched (Config will use its fallback)"
    exit 0
fi

PLIST="${BUILT_PRODUCTS_DIR}/${INFOPLIST_PATH}"
/usr/libexec/PlistBuddy -c "Set :DevLANHost ${IP}" "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :DevLANHost string ${IP}" "$PLIST"

echo "inject-dev-host: DevLANHost = ${IP}"
