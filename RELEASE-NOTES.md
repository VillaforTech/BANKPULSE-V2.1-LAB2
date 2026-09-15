# BankPulse V2.1 — Interactive banking experience

## Product direction

V2.1 preserves the six deployable services, data ownership, CI and observability from V2.0, while making an interactive banking frontend connected to the running APIs the primary experience.

## Product capabilities
- Client Mode y Architect Mode.
- Home bancario con health de seis servicios y datos del core financiero.
- Experiencias gastronómicas cargadas desde `experiences-api` y garantía demo vía `payments-api`.
- Viajes: eligibility + credencial HMAC + simulación offline local.
- Eventos: mapa de asientos, HOLD real en Redis, TTL visible, conflicto HTTP 409 y liberación.
- Social Split: sesión real, participantes, pagos reales, referencias financieras y cierre condicionado.
- Platform view: health, visual C4 model, data ownership, request trace and links to Grafana, Prometheus and cAdvisor.
- Endpoint `GET /api/events/{eventId}/holds` for controlled inspection of active holds.

## Security and architecture
- Los puertos 8081-8086 siguen internos a Docker.
- El navegador entra por Nginx `:8080`.
- La UI no obtiene acceso directo a bases de datos.
- The visual request trace is derived from client calls and does not replace distributed tracing such as OpenTelemetry.
- Redis key inspection supports the local visualization; a production implementation should use a bounded index or SCAN strategy.

## Compatibilidad
CI, observabilidad, Docker Compose, Codespaces y el fix Yarn de V2.0 se mantienen.

## Documentation added
- `docs/architecture/INTERACTIVE-FRONTEND.md`
- `docs/TEST-PLAN-V2.1.md`
