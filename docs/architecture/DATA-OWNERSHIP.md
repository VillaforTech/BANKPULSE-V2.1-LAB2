# BANKdragon V2 - Data Ownership Matrix

La regla principal es **database/schema per bounded context**. Ningun microservicio puede escribir directamente en la persistencia de otro servicio. Una copia local puede existir como proyeccion, pero la autoridad sigue perteneciendo al owner indicado.

| Servicio | Bounded context / epica | Datos de los que es autoridad | Persistencia | Integracion permitida |
|---|---|---|---|---|
| `experiences-api` | Gastronomia | Experience, Restaurant/Partner metadata, Menu/Offer catalog | MongoDB database `experiences` | REST/eventos; nunca acceso a Payments DB |
| `travel-benefits-api` | Viajes | Eligibility, Credential, Redemption | MongoDB database `travel` | Credenciales firmadas; sincronizacion diferida |
| `events-api` | Eventos | Event, Venue, Seat/Availability, temporal Hold | PostgreSQL schema `events` + Redis TTL | REST/eventos hacia Payments; Redis no es ledger financiero |
| `social-split-api` | Social Split | SplitSession, Participant, Share, authorization reference | PostgreSQL schema `social_split` | Payments por API/eventos; solo almacena `paymentReference` |
| `payments-api` | Core Financiero | Payment, Authorization/financial state, Outbox | MariaDB database `bankpulse` | API financiera; publica auditoria via outbox |
| `audit-api` | Auditoria | AuditEvent immutable projection | MongoDB database `audit` | Consume eventos; no modifica dominios origen |

## Reglas de arquitectura

1. **Single writer:** solo el owner escribe su modelo canonico.
2. **No shared tables:** ningun servicio consulta tablas/esquemas de otro bounded context.
3. **Reference over replication:** cuando sea suficiente, almacenar IDs (`paymentReference`) y no el objeto financiero completo.
4. **Eventual consistency is explicit:** proyecciones y auditoria pueden retrasarse; el contrato debe declarar ese comportamiento.
5. **Strong consistency where it matters:** asignacion persistente de localidades y estados financieros requieren controles transaccionales.
6. **Ephemeral state is not source of truth:** Redis se utiliza para holds con TTL, no como ledger definitivo.
7. **Observability is part of the contract:** cada servicio expone `/actuator/health` y `/actuator/prometheus`.

## Preguntas obligatorias para cada ADR de equipo

- Que agregado posee el servicio?
- Quien es el source of truth?
- Que datos puede duplicar y por cuanto tiempo?
- Que operaciones requieren consistencia fuerte?
- Que operaciones toleran consistencia eventual?
- Como reacciona ante caida de otro servicio?
- Como evita acceso directo a bases de datos ajenas?
- Que metricas demuestran que el modelo funciona?
