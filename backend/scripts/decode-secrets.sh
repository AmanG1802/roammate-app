#!/bin/sh
# Decodes base64-encoded Apple key env vars into /app/secrets/ before app start.
# Set APPLE_MAPS_PRIVATE_KEY_B64, APPLE_SIGNIN_PRIVATE_KEY_B64, APPLE_PRIVATE_KEY_B64,
# APPLE_ROOT_CA_B64, and APNS_PRIVATE_KEY_B64 in Railway to populate these files.
mkdir -p /app/secrets

[ -n "$APPLE_MAPS_PRIVATE_KEY_B64"   ] && printf '%s' "$APPLE_MAPS_PRIVATE_KEY_B64"   | base64 -d > /app/secrets/AuthKey_R4KAG8ZD76.p8
[ -n "$APPLE_SIGNIN_PRIVATE_KEY_B64" ] && printf '%s' "$APPLE_SIGNIN_PRIVATE_KEY_B64" | base64 -d > /app/secrets/AuthKey_MU3GJ2B59Z.p8
[ -n "$APPLE_PRIVATE_KEY_B64"        ] && printf '%s' "$APPLE_PRIVATE_KEY_B64"        | base64 -d > /app/secrets/AuthKey_56XQPP7NWX.p8
[ -n "$APPLE_ROOT_CA_B64"            ] && printf '%s' "$APPLE_ROOT_CA_B64"            | base64 -d > /app/secrets/AppleRootCA-G3.cer
[ -n "$APNS_PRIVATE_KEY_B64"         ] && printf '%s' "$APNS_PRIVATE_KEY_B64"         | base64 -d > /app/secrets/AuthKey_3H5GT2DU52.p8

exec "$@"
