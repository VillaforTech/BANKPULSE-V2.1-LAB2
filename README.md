# BANKdragon / BankPulse V2.1 — Interactive Banking Experience

> **V2.1:** además de la plataforma de microservicios, el puerto `8080` ofrece una experiencia bancaria interactiva con modos Cliente/Arquitecto, gastronomía, viajes offline, seat holds, Social Split y visualización de arquitectura. Todo consume APIs reales del laboratorio.

Plataforma docente de microservicios desplegables para Arquitectura de Software, DDD, DevOps, CI y Observabilidad. Esta version conserva el core financiero de BankPulse y transforma las cuatro epicas de negocio en servicios independientes con contratos, ownership de datos, health checks y metricas.

## Arquitectura V2

| Servicio | Epica / contexto | Puerto interno | Persistencia |
|---|---|---:|---|
| `payments-api` | Core financiero | 8081 | MariaDB |
| `audit-api` | Auditoria | 8082 | MongoDB `audit` |
| `experiences-api` | Gastronomia | 8083 | MongoDB `experiences` |
| `travel-benefits-api` | Viajes | 8084 | MongoDB `travel` |
| `events-api` | Eventos premium | 8085 | PostgreSQL `events` + Redis TTL |
| `social-split-api` | Social Split | 8086 | PostgreSQL `social_split` |
| `console` | Edge + UI | 8080 host | Nginx |

Los puertos 8081-8086 permanecen dentro de la red Docker. El navegador entra por `console:8080`, que funciona como edge/reverse proxy de laboratorio.


## Frontend interactivo V2.1

La UI del puerto `8080` ahora permite recorrer las cuatro épicas desde una experiencia bancaria:

- **Experiencias:** consulta MongoDB a través de `experiences-api` y genera una garantía demo en `payments-api`.
- **Viajes:** consulta elegibilidad, emite credencial firmada y permite demostrar disponibilidad offline local.
- **Eventos:** renderiza un mapa de asientos y crea HOLDs reales en Redis con TTL; un segundo intento obtiene HTTP 409.
- **Social Split:** crea sesiones/participantes reales, usa referencias de pagos y aplica la invariante de cierre.
- **Platform:** muestra health de seis servicios, C4 simplificado, ownership y enlaces a la observabilidad real.

Use el selector **Cliente / Arquitecto** para alternar entre experiencia de usuario y explicaciones técnicas.

## Data ownership

La V2 aplica **single-writer ownership**. Compartir un motor fisico en Codespaces no significa compartir modelo de datos:

- `payments-api` es la unica autoridad financiera.
- `events-api` posee eventos y holds; Redis solo contiene estado temporal.
- `social-split-api` almacena referencias de pago, no transacciones financieras.
- `experiences-api` y `travel-benefits-api` usan bases Mongo separadas.
- `audit-api` es una proyeccion de auditoria y no modifica dominios de origen.

Consulte `docs/architecture/DATA-OWNERSHIP.md` y use `docs/adr/ADR-TEMPLATE-DATA-OWNERSHIP.md` como entregable de equipo.

## Inicio rapido en GitHub Codespaces

El Dev Container incluye el fix de Yarn requerido por Docker-in-Docker:

```dockerfile
FROM mcr.microsoft.com/devcontainers/java:1-21-bookworm
RUN rm -f /etc/apt/sources.list.d/yarn.list
```

1. Abra **Code -> Codespaces -> Create codespace on main**.
2. Espere el build inicial de los servicios.
3. Verifique:

```bash
docker --version
docker compose version
docker compose ps
```

4. Abra el puerto **8080** reenviado por Codespaces.

No se requiere IP del Codespace.

## Inicio manual

```bash
cp .env.example .env
docker compose config
docker compose up -d --build --wait
docker compose ps
```

Prueba integral:

```bash
bash scripts/smoke-v2.sh
```

## Observabilidad

El stack se mantiene separado de la aplicacion:

```bash
docker compose -f observability/compose.yaml up -d
docker compose -f observability/compose.yaml ps
```

Puertos de Codespaces:

- 3000: Grafana
- 9090: Prometheus
- 8088: cAdvisor

Grafana demo:

- usuario: `admin`
- password: `bankpulse_demo`

Estas credenciales son exclusivamente docentes. Para produccion use un secret manager.

Prometheus scrapea `/actuator/prometheus` de los seis microservicios. El dashboard `BANKdragon V2 Platform Overview` incluye disponibilidad, throughput HTTP, heap JVM, p95 y CPU de contenedores.

## CI

`.github/workflows/ci.yml` implementa dos puertas:

1. **Architecture contract:** verifica la existencia de los seis servicios, ownership docs y Compose/observabilidad validos.
2. **Integration test:** construye el stack real, ejecuta `smoke-v2.sh`, levanta Prometheus/Grafana y valida sus health endpoints.

Flujo esperado:

```text
feature/* -> Pull Request -> GitHub Actions -> CI verde -> review -> squash merge -> main
```

CI no significa deployment. El workflow demuestra integrabilidad y calidad automatizada; CD puede incorporarse posteriormente con GHCR + Argo CD/Kubernetes.

## Distribucion por equipos

- Equipo Gastronomia -> `services/experiences-api`
- Equipo Viajes -> `services/travel-benefits-api`
- Equipo Eventos -> `services/events-api`
- Equipo Social Split -> `services/social-split-api`

Cada equipo debe entregar DDD, C4, ADR de Data Ownership, implementacion, tests, evidencia CI y metricas operacionales.

## Recursos de Codespaces

La configuracion objetivo es 4 CPU / 8 GB. La persistencia comparte motores fisicos para no multiplicar consumo, manteniendo aislamiento logico. Al terminar:

```bash
docker compose -f observability/compose.yaml down
docker compose down
```

Luego use **Stop Codespace**.

## Seguridad

No suba `.env`, tokens, claves institucionales o credenciales reales. Los passwords incluidos son solamente para un entorno local efimero de aprendizaje.
