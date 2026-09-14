# 2. Respect data ownership across six services

Date: 2026-09-13

## Status

Accepted

## Context

BANKdragon separa pagos, auditoría, experiencias, viajes, eventos y Social Split.
Este registro documenta retrospectivamente la regla ya presente en la
[matriz de ownership](../architecture/DATA-OWNERSHIP.md) y en la composición
actual del laboratorio. La fecha corresponde al registro, no a una nueva
migración ni a la aprobación de una implementación pendiente.

## Decision

Mantener un único escritor por contexto y usar API o eventos para cruzar sus
límites. La autoridad se distribuye así:

| Servicio | Datos propios | Persistencia |
| --- | --- | --- |
| `payments-api` | Pagos, autorizaciones y outbox financiero | MariaDB `bankpulse` |
| `audit-api` | Proyección de eventos de auditoría | MongoDB `audit` |
| `experiences-api` | Experiencias, partners y ofertas | MongoDB `experiences` |
| `travel-benefits-api` | Elegibilidad, credenciales y canjes | MongoDB `travel` |
| `events-api` | Eventos, localidades y disponibilidad persistente | PostgreSQL `events`; Redis para holds con TTL |
| `social-split-api` | Sesiones, participantes y cuotas | PostgreSQL `social_split` |

Social Split conserva la referencia del pago; Payments mantiene la autoridad
financiera. Auditoría es una proyección y no modifica los dominios de origen.
Redis conserva estado temporal y no sustituye el registro persistente. Aunque
se comparta un motor físico, los contextos no comparten tablas ni escritores.

Se descarta que todos los servicios escriban una base común: simplificaría
algunas consultas, pero acoplaría cambios de esquema y diluiría la autoridad.
Se descarta consultar directamente la base de otro contexto por el mismo motivo.

## Consequences

Cada servicio puede evolucionar su modelo, a costa de integrar mediante
contratos y tolerar dependencias no disponibles. Las proyecciones admiten
consistencia eventual; los estados financieros y la asignación persistente de
localidades requieren controles transaccionales. No se debe asumir frescura
inmediata de auditoría ni de una copia local.

La matriz define qué puede duplicarse y la observabilidad mediante health y
métricas. Los fallos de dependencias deben quedar visibles y manejarse en la
API o el consumidor; esta decisión no autoriza acceso directo a una base ajena
como mecanismo de recuperación.

La existencia de este ADR y su validación documental no prueban idempotencia,
consistencia o recuperación. Esas garantías necesitan las pruebas de aplicación
correspondientes, que conservan su alcance en el plan de trabajo del equipo.
