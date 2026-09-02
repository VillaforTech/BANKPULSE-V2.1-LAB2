# BANKpulse V2.1 — Interactive Frontend Architecture

## Purpose
The V2.1 frontend is a thin educational edge UI. It demonstrates real domain behavior without taking ownership away from the microservices.

## Runtime topology

```text
Browser
  |
  v
Nginx console :8080
  |-- /api/experiences -> experiences-api :8083
  |-- /api/travel      -> travel-benefits-api :8084
  |-- /api/events      -> events-api :8085
  |-- /api/splits      -> social-split-api :8086
  |-- /api/payments    -> payments-api :8081
  `-- /api/audit       -> audit-api :8082
```

The browser never connects to MariaDB, MongoDB, PostgreSQL or Redis directly.

## Client Mode
Focuses on the banking/customer experience:
- home and recent payments;
- gastronomy experiences;
- travel eligibility and credential;
- event seat selection;
- collaborative split flow.

## Architect Mode
Adds educational explanations:
- ownership boundaries;
- C4-like container flow;
- health of all six services;
- teaching trace based on UI requests;
- links to real Prometheus/Grafana/cAdvisor.

The teaching trace is intentionally not called distributed tracing. It records the path the UI invoked and measured client-perceived latency. OpenTelemetry can be added later as a DevSecOps/observability evolution.

## Domain interactions

### Experiences
The UI reads `experiences-api`. A guarantee demo creates a payment using `payments-api`. The financial transaction remains owned by Payments.

### Travel
The UI obtains eligibility and a signed demo credential. The last credential is stored in browser local storage only to illustrate an offline-first experience. This is a teaching mechanism, not a production credential wallet.

### Events
The seat map calls the real Events API. Holds are atomic Redis SET-if-absent values with TTL. `GET /api/events/{eventId}/holds` exists only as lab introspection for rendering active holds. Its current Redis `KEYS` implementation must not be copied to large production datasets.

### Social Split
The UI creates the Split Session in `social-split-api`. When a participant authorizes, the UI creates a real payment and passes only the payment reference to Social Split. This visibly demonstrates data ownership.

## Security boundaries
- Nginx remains the only browser-facing application port.
- Service ports 8081-8086 remain internal to the Docker network.
- Existing CSP and security headers remain active.
- No institutional secrets are embedded in the frontend.
- Grafana demo credentials remain lab-only.

## Production evolution
For a production-grade architecture, evolve the edge into an API Gateway/BFF, replace teaching trace with OpenTelemetry, move cross-domain orchestration out of the browser, introduce OIDC/JWT, and use a secret manager.
