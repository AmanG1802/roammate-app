# backend/secrets/

This directory holds private keys and certificates that **must never be committed**.

The directory itself is gitignored (`backend/secrets/` in repo `.gitignore`),
so this README is the only file Git will ever see from here.

## Expected contents

- `app_store_server.p8` — App Store Server API signing key
  (from App Store Connect → Users and Access → Integrations).
- `AppleRootCA-G3.cer` — Apple Root CA used to verify JWS/JWE signatures
  on StoreKit transactions and SSN V2 webhook envelopes.
  Download from <https://www.apple.com/certificateauthority/AppleRootCA-G3.cer>.
- `apns.p8` — Apple Push Notifications signing key (when push is wired).
- `mapkit.p8` — Apple Maps Server API signing key (when MapKit is wired).
- `siwa.p8` — Sign in with Apple signing key (when SIWA is wired).

## Setup

```bash
curl -o backend/secrets/AppleRootCA-G3.cer \
  https://www.apple.com/certificateauthority/AppleRootCA-G3.cer
```

Then drop your downloaded `.p8` files in alongside it and point the
corresponding `APPLE_*_PRIVATE_KEY_PATH` / `APPLE_ROOT_CA_PATH` env vars
at them (see `.env.example`).
