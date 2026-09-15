# Contrato de eventos Social Split v1

Fuente autoritativa para la integración con `business-analytics`. El contrato coincide con `services/business-analytics/README.md` de `feature/deber-01-business-analytics`; esa ruta aún no existe en `main` de este repositorio.

- Topic: `bankpulse.social-split.events.v1`
- Clave Kafka: `aggregateId`
- Grupo consumidor: `bankpulse-business-analytics-v1`
- `schemaVersion`: `1`
- `occurredAt`: UTC ISO-8601
- Cada `eventId` es UUID estable y se conserva durante los reintentos.

Envelope:

```json
{"eventId":"uuid","eventType":"SplitCreated","schemaVersion":1,"aggregateId":"split-1","aggregateVersion":1,"occurredAt":"2026-09-15T12:00:00Z","payload":{}}
```

## Eventos

```json
{"eventId":"e1","eventType":"SplitCreated","schemaVersion":1,"aggregateId":"split-1","aggregateVersion":1,"occurredAt":"2026-09-15T12:00:00Z","payload":{"sessionId":"split-1","createdAt":"2026-09-15T12:00:00Z","totalAmount":100,"currency":"USD"}}
```

```json
{"eventId":"e2","eventType":"ParticipantAdded","schemaVersion":1,"aggregateId":"split-1","aggregateVersion":2,"occurredAt":"2026-09-15T12:00:01Z","payload":{"participantId":"p1","memberId":"member-1","shareAmount":60}}
```

```json
{"eventId":"e3","eventType":"ParticipantAuthorized","schemaVersion":1,"aggregateId":"split-1","aggregateVersion":3,"occurredAt":"2026-09-15T12:00:02Z","payload":{"participantId":"p1","paymentReference":"present"}}
```

```json
{"eventId":"e4","eventType":"SplitCompleted","schemaVersion":1,"aggregateId":"split-1","aggregateVersion":4,"occurredAt":"2026-09-15T12:00:03Z","payload":{"closedAt":"2026-09-15T12:00:03Z"}}
```

No event contains `valid` or `ok`. `paymentReference` is the contract field carrying the literal presence marker `present`; real payment references and personal data are not sent. The consumer reconstructs shares, total, authorizations and reference presence from the facts and derives KPI validity itself.

The outbox and domain transition use one JPA/Postgres transaction. A rollback creates no event. After commit the relay waits for Kafka acknowledgement and retries the same envelope; a crash after send and before marking published may redeliver the same `eventId`, which the consumer must deduplicate.