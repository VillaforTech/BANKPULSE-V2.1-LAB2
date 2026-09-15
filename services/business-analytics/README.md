# BankPulse Business Analytics — Issue #2

Procesador independiente para los KPI B-K1, B-K2 y B-K3 del Deber 01. Consume hechos de Social Split, conserva su propia proyección y publica snapshots para Grafana Live. No lee ni escribe la base de Social Split.

## Alcance demostrado

- B-K1: `100 × cierres íntegros / cierres` en una ventana semiabierta de 15 minutos basada en `closedAt`.
- B-K2: descuadre absoluto de cierres por moneda dentro de esa ventana.
- B-K3: cuotas autorizadas por moneda en sesiones `OPEN` con edad estrictamente mayor a 120 segundos.
- `SIN MUESTRA` para B-K1 sin cierres; importes exactos con `Decimal`.
- Inbox idempotente, versiones consecutivas, eventos fuera de orden y checkpoints atómicos en SQLite.
- Rehidratación tras reinicio y reloj de 200 ms para vencimientos y expiración de ventanas sin tráfico.
- Estados `ACTUAL`, `DESACTUALIZADO` e `INCOMPLETO`, sin presentar errores como ceros sanos.
- Historial de snapshots, SSE y métricas Prometheus.

Relacionado con la asignación [#2](https://github.com/VillaforTech/BANKPULSE-V2.1-LAB2/issues/2).

## Contrato de entrada preparado para #1

Topic: `bankpulse.social-split.events.v1`
Grupo: `bankpulse-business-analytics-v1`
Clave Kafka: `aggregateId` de la sesión.

Envelope común versión 1:

```json
{
  "eventId": "uuid-estable",
  "eventType": "SplitCreated",
  "schemaVersion": 1,
  "aggregateId": "split-id",
  "aggregateVersion": 1,
  "occurredAt": "2026-09-15T12:00:00Z",
  "payload": { "sessionId": "split-id" }
}
```

Transiciones soportadas:

| Evento | Campos adicionales del payload |
| --- | --- |
| `SplitCreated` | `createdAt`, `totalAmount`, `currency` |
| `ParticipantAdded` | `participantId`, `memberId`, `shareAmount` |
| `ParticipantAuthorized` | `participantId`, `paymentReference` |
| `SplitCompleted` | `closedAt`, igual a `occurredAt` |

El consumidor reconstruye la sesión desde los datos, sin confiar en un campo `valid`. Por eso una transición `SplitCompleted` bien formada con cuotas 60+30 sobre total 100 se conserva y se observa como B-K1 incumplido y B-K2 USD 10. El documento final de #1 sigue siendo la fuente autoritativa; cualquier diferencia debe resolverse antes de integrar ambos PR.

## Snapshot para #3

- `GET /snapshot`: último snapshot completo.
- `GET /updates?after=<revision>`: recuperación paginada por revisión.
- `GET /stream?after=<revision>`: SSE para actualizaciones continuas.
- `GET /health`: vida del proceso.
- `GET /ready`: 200 solo cuando cobertura y frescura permiten declarar el snapshot válido.
- `GET /metrics`: agregados y salud Prometheus.

Cada snapshot contiene `revision`, `dataRevision`, `generatedAt`, `lastEventId`, `quality`, `valid`, valores/unidades/muestras, alertas, cobertura, frescura y diagnóstico. Una caída del consumidor vuelve la vista `DESACTUALIZADO`; huecos o errores la vuelven `INCOMPLETO`. Los valores provisionales permanecen visibles, pero `valid=false` y las alertas no afirman un estado sano.

## Persistencia y entrega Kafka

`Store.ingest` guarda inbox, proyección y siguiente offset local en una transacción SQLite. El runtime confirma después el offset en Kafka. Un fallo entre ambos pasos produce reentrega y el `eventId` evita el doble efecto. Esto ofrece entrega al menos una vez con efecto idempotente; no se afirma exactly-once.

El consumidor usa el checkpoint local como autoridad al reiniciar. Un inicio posterior a la retención disponible marca `historyMissing`. La implementación usa un proceso y un worker Uvicorn porque SQLite es el almacenamiento independiente disponible en esta rama; #4 puede sustituirlo al integrar el almacenamiento acordado.

## Configuración

| Variable | Valor por defecto |
| --- | --- |
| `KAFKA_BOOTSTRAP` | `redpanda:9092` |
| `ANALYTICS_DB` | `/data/analytics.sqlite` |
| `ANALYTICS_COVERAGE_FROM` | sin cobertura completa |
| `ANALYTICS_TICK_SECONDS` | `0.2` (admite 0.1–0.25) |
| `ANALYTICS_STALE_OPEN_SECONDS` | `120` |

`ANALYTICS_COVERAGE_FROM` identifica la población retenida y queda inmutable en la base. Sin ese dato, la salida permanece `INCOMPLETO`.

## Validación local

Desde `services/business-analytics`:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-test.txt
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check analytics tests
.venv/Scripts/python -m ruff format --check analytics tests
docker compose -f compose.test.yaml config --quiet
docker compose -f compose.test.yaml up -d --build --wait
python tests/integration.py --docker docker --output integration-evidence.json
docker compose -f compose.test.yaml down
```

El test integrado exige un volumen nuevo del Compose aislado. No borra datos automáticamente. Ese Compose configura el deadline en 3 segundos para observar ambos lados del temporizador; el servicio conserva 120 segundos como valor predeterminado.

Replay reproducible con reloj controlado:

```bash
python -m analytics.replay tests/fixtures/social_split.ndjson \
  --db replay.sqlite \
  --coverage-from 2033-05-18T03:33:20Z \
  --at 2033-05-18T03:35:30Z
```

El replay se niega a sobrescribir una base existente.

## Coordinación pendiente

- #1: confirmar y versionar el contrato productor/outbox.
- #3: conectar snapshot y stream a Grafana Live.
- #4: aprovisionar topic, volumen, servicio y checks del Release Gate.
- #5: reutilizar fixture, replay y oráculo para las pruebas E2E y de falso verde.
