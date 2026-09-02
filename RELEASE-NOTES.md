# BANKdragon / BankPulse V2.1 — Interactive Banking Experience

## Objetivo
V2.1 conserva los seis microservicios desplegables, data ownership, CI y observabilidad de V2.0, y reemplaza la consola técnica como experiencia principal por un frontend bancario interactivo conectado a APIs reales.

## Nuevas capacidades
- Client Mode y Architect Mode.
- Home bancario con health de seis servicios y datos del core financiero.
- Experiencias gastronómicas cargadas desde `experiences-api` y garantía demo vía `payments-api`.
- Viajes: eligibility + credencial HMAC + simulación offline local.
- Eventos: mapa de asientos, HOLD real en Redis, TTL visible, conflicto HTTP 409 y liberación.
- Social Split: sesión real, participantes, pagos reales, referencias financieras y cierre condicionado.
- Platform view: health, C4 visual, data ownership, trace de enseñanza y enlaces a Grafana/Prometheus/cAdvisor.
- Endpoint `GET /api/events/{eventId}/holds` para introspección controlada del laboratorio.

## Seguridad/arquitectura
- Los puertos 8081-8086 siguen internos a Docker.
- El navegador entra por Nginx `:8080`.
- La UI no obtiene acceso directo a bases de datos.
- La traza visual es una traza didáctica derivada de las llamadas del cliente; no sustituye OpenTelemetry.
- La enumeración Redis usada para visualizar holds está marcada como mecanismo docente; producción debe usar un índice/SCAN acotado.

## Compatibilidad
CI, observabilidad, Docker Compose, Codespaces y el fix Yarn de V2.0 se mantienen.

## Documentation added
- `docs/architecture/INTERACTIVE-FRONTEND.md`
- `docs/TEST-PLAN-V2.1.md`
