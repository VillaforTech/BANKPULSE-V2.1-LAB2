# BANKpulse V2.1 Acceptance Test

Run this test in a **new GitHub Codespace** created from the repository after V2.1 is committed.

## 1. Environment
```bash
docker --version
docker compose version
```

## 2. Platform
```bash
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 300
docker compose ps
```
Expected: all six APIs and data services healthy; console Up.

## 3. Automated regression
```bash
bash scripts/smoke-v2.sh
```
Expected: `BANKdragon V2.1 interactive smoke test OK`.

## 4. Interactive UI
Open Codespaces port 8080 and verify:
- Home shows six service health states.
- Experiences shows seeded catalog and creates a payment guarantee.
- Travel issues a credential and preserves it when Offline mode is enabled.
- Events displays seats, creates a Redis HOLD, shows countdown and returns 409 when another client holds the same seat.
- Social Split creates a session, participants, payments, authorizations and then allows close.
- Architect Mode shows ownership explanations and teaching traces.

## 5. Observability
```bash
docker compose -f observability/compose.yaml up -d
docker compose -f observability/compose.yaml ps
```
Open 3000, 9090 and 8088 through Codespaces Ports.

## 6. CI
Create a feature branch and Pull Request to main. Required GitHub Actions jobs:
- Architecture contract
- Build, integration and observability

Both must be green before merge.
