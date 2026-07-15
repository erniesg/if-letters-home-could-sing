# Frontend workspace

This directory preserves the earlier Next.js heartbeat-responsive prototype while the reMarkable correspondence experience is developed behind fixture providers.

Use Node `22.22.3` and npm `10.9.8`; dependency versions are exact in `package.json` and `package-lock.json`:

```bash
nvm use
npm ci
npm run type-check
npm run dev
```

The WHOOP access token is server-side configuration only. Never print it, any substring of it, authorization headers, provider payloads, or heart-rate samples. Live WHOOP and BLE work remains a human-approved trusted-VM lane; portable tests use fixtures.
