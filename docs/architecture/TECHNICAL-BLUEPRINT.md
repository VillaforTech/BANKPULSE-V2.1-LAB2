# BANKdragon V2 - Technical Blueprint

## Objetivo
Convertir las cuatro epicas DDD en servicios desplegables sin perder el core financiero y la auditoria existentes. La V2 prioriza limites de dominio, ownership de datos, CI reproducible y observabilidad integrada.

## Servicios desplegables

### experiences-api - Epica Gastronomia
- Puerto interno: 8083
- Persistencia: MongoDB / `experiences`
- Endpoints base: `GET/POST /api/experiences`
- Ownership: catalogo de experiencias y metadatos comerciales.
- Extension de equipo: disponibilidad, reserva/garantia, geolocalizacion y partner contracts.

### travel-benefits-api - Epica Viajes
- Puerto interno: 8084
- Persistencia: MongoDB / `travel`
- Endpoints base: eligibility, credential, redemption.
- Incluye credencial HMAC de demostracion para discutir validacion offline.
- Extension: revocacion, anti-replay, sincronizacion y modelo de riesgo.

### events-api - Epica Eventos
- Puerto interno: 8085
- Persistencia canonica: PostgreSQL schema `events`
- Estado efimero: Redis hold con TTL.
- El endpoint de hold usa `SETNX + TTL`, permitiendo discutir concurrencia real.
- Extension: mapa de asientos, confirmacion con Payments, Saga y waiting room.

### social-split-api - Epica Social Split
- Puerto interno: 8086
- Persistencia: PostgreSQL schema `social_split`
- Mantiene sesion, participantes, shares y referencia de pago.
- No posee Payment ni Authorization.
- Extension: reparto exacto, expiracion, compensaciones y eventos.

### payments-api
- Puerto interno: 8081
- MariaDB
- Idempotencia + Transactional Outbox.

### audit-api
- Puerto interno: 8082
- MongoDB
- Proyeccion de eventos de auditoria.

## Persistencia fisica vs ownership logico
Para conservar un Codespace de 4 CPU/8 GB, V2 comparte motores fisicos en laboratorio, pero mantiene aislamiento logico:
- MongoDB: bases separadas `audit`, `experiences`, `travel`.
- PostgreSQL: usuarios/esquemas separados `events` y `social_split`.
- MariaDB: exclusivamente core financiero.
- Redis: exclusivamente estado temporal de Events.
En produccion, cada owner podria moverse a instancias administradas independientes sin cambiar el contrato de dominio.

## Requisitos no funcionales base
- Health endpoints y metricas Prometheus en todos los servicios.
- Contenedores ejecutados como usuario no-root.
- Secrets solo por variables de entorno; valores del repositorio son exclusivos de laboratorio.
- APIs internas no publicadas al host; acceso externo por edge Nginx.
- CI levanta el sistema real y ejecuta smoke tests.
- Observabilidad valida los seis servicios y el runtime Docker.
