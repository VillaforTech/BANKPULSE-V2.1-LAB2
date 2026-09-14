# Deber 01 — El falso verde (BANKPULSE / Social Split)

**Repositorio:** BANKPULSE-V2.1-LAB2
**Issue:** [#5](https://github.com/VillaforTech/BANKPULSE-V2.1-LAB2/issues/5) — Pruebas de extremo a extremo, resiliencia y evidencia del falso verde
**Autor:** Daniel (`@Dmt-155lbs`)
**Rama de evidencia:** `feat/5-deber-01-harness`

> **Nota de estado.** Este documento se redacta con el harness de pruebas ya escrito (`scripts/acceptance/`, `tests/kpis/`, `fixtures/`) pero **antes** de ejecutarlo contra un despliegue real y **antes** de que existan PR, corridas de CI o capturas del proyecto. Toda sección o celda marcada `PENDIENTE` describe un resultado **esperado/diseñado**, no uno **observado**. Ninguna cifra de latencia, ningún SHA de commit, ninguna URL de PR ni ningún run id de GitHub Actions mostrados aquí son inventados: donde el dato todavía no existe, se deja `PENDIENTE` explícitamente para que Daniel lo complete con evidencia real.

## Tabla de contenidos

1. [Capacidad de negocio seleccionada](#1-capacidad-de-negocio-seleccionada)
2. [Escenario de falso verde](#2-escenario-de-falso-verde)
3. [Riesgo / pérdida potencial](#3-riesgo--pérdida-potencial)
4. [KPIs propios](#4-kpis-propios)
5. [Arquitectura y semántica temporal](#5-arquitectura-y-semántica-temporal)
6. [Diagrama del Release Gate](#6-diagrama-del-release-gate)
7. [Evidencia: PR sano (verde)](#7-evidencia-pr-sano-verde)
8. [Evidencia: PR con tecnología verde y negocio rojo](#8-evidencia-pr-con-tecnología-verde-y-negocio-rojo)
9. [Evidencia del bloqueo efectivo del merge](#9-evidencia-del-bloqueo-efectivo-del-merge)
10. [Diagnóstico y corrección](#10-diagnóstico-y-corrección)
11. [Ejecución final verde](#11-ejecución-final-verde)
12. [Cómo reproducir desde un Codespace limpio](#12-cómo-reproducir-desde-un-codespace-limpio)
13. [Tabla de contribuciones del equipo](#13-tabla-de-contribuciones-del-equipo)
14. [Checklist de la rúbrica 3+5+2](#14-checklist-de-la-rúbrica-352)
15. [Límites del benchmark de laboratorio](#15-límites-del-benchmark-de-laboratorio)

---

## 1. Capacidad de negocio seleccionada

**Capacidad protegida:** *un compromiso compartido (Social Split) solo se cierra con el consentimiento de todos los participantes y con cobertura exacta del total.*

`services/social-split-api` implementa `SplitSession` con un ciclo `OPEN -> COMPLETED`: se crea la sesión con un `totalAmount`, se agregan participantes con su `shareAmount`, cada participante se autoriza con una `paymentReference`, y `POST /api/splits/{id}/close` invoca `closeIfAuthorized()` para cerrar la sesión.

## 2. Escenario de falso verde

Un **falso verde** ocurre cuando la sesión queda `COMPLETED` con HTTP 2xx y toda la infraestructura sana (API, base de datos y contenedores `UP`), pese a que la capacidad protegida está violada.

**Defecto real confirmado en el código** (`services/social-split-api/src/main/java/com/bankpulse/split/SplitSession.java`):

```java
public void closeIfAuthorized(){
  if(participants.isEmpty()||participants.stream().anyMatch(p->!p.isAuthorized()))
    throw new IllegalStateException("all participants must authorize");
  status="COMPLETED";
}
```

`closeIfAuthorized()` **solo** valida que existan participantes y que todos estén autorizados. **No valida en ningún momento que la suma de `shareAmount` autorizados sea igual a `totalAmount`.** Hoy se puede cerrar una sesión con `totalAmount = 100.00` y cuotas autorizadas `60.00 + 30.00 = 90.00` (descuadre de `10.00`), y la API responde con `status = "COMPLETED"` y HTTP 2xx.

Corregir `closeIfAuthorized()` es trabajo del **issue #1**; el issue #5 (este documento y su harness) únicamente **detecta y evidencia** el defecto, sin corregirlo.

**Caso de aceptación fijado por el issue #5** (documentado también en `fixtures/bankpulse/cierre-descuadrado-60-30.json` y ejercitado por `scripts/acceptance/business_test_social_split.py::escenario_falso_verde`):

> Cierre de una sesión con `totalAmount = 100.00`, cuotas autorizadas `60.00` y `30.00` (suman `90.00`) → la API real deja el cierre en `COMPLETED` con HTTP 2xx, con un descuadre de `10.00`.

## 3. Riesgo / pérdida potencial

Los montos siguientes están expresados en **unidades monetarias de laboratorio** (datos demo generados para el ejercicio). No representan USD, no representan ingresos perdidos ni una pérdida financiera demostrada; BankPulse es un laboratorio y ninguna de estas sesiones mueve dinero real. Estos números son exposición/descuadre de una demo académica.

Para el caso de aceptación (cierre `60 + 30` de un total `100`):

| Magnitud | Valor | Unidad |
|---|---:|---|
| Cierres íntegros (B-K1) | < 100 | % de la cohorte cerrada en la ventana |
| Descuadre monetario al cerrar (B-K2) | 10.00 | unidades monetarias demo, por moneda (`USD`) |

## 4. KPIs propios

Los KPIs son funciones puras implementadas en `tests/kpis/bank_kpis.py` (sin red, sin base de datos; reciben la lista de sesiones y el instante `ahora` inyectado, usando siempre `Decimal` para montos) y verificadas con `tests/kpis/test_bank_kpis.py`.

| KPI | Nombre | Fórmula | Población | Ventana | Umbral |
|---|---|---|---|---|---|
| **B-K1** | Cierres íntegros | `100 * cierres_validos / sesiones_cerradas_en_ventana` | Sesiones con `closedAt` dentro de la ventana. Un cierre es "válido" si tiene participantes no vacíos, cuotas positivas que suman **exactamente** `totalAmount`, todos autorizados y con `paymentReference` no vacía | 900 s (15 min) | **100 %** — sin sesiones cerradas en la ventana se reporta `"SIN MUESTRA"`, nunca `0.0` ni `100.0` |
| **B-K2** | Descuadre monetario al cerrar | `Σ abs(totalAmount - Σ cuotas_autorizadas)` de las sesiones cerradas en la ventana, **cada moneda mantenida por separado** (nunca se convierten ni se suman entre sí) | Sesiones cerradas en la ventana | 900 s (15 min) | **0** por moneda |
| **B-K3** | Importe autorizado sin resolución en sesiones abiertas | `Σ cuotas_autorizadas` de sesiones todavía `OPEN` cuya edad (`ahora - createdAt`) supera 120 s, por moneda | Sesiones `OPEN` (backlog completo, sin ventana de 15 min) | Foto del instante `ahora`, edad mínima 120 s | **0** por moneda |

Reglas de diseño verificadas en el código:

- `B-K1` nunca reporta `0.0` ni `100.0` cuando no hay sesiones cerradas en la ventana: devuelve el literal `"SIN MUESTRA"` (`calcular_b_k1`, `bank_kpis.py`).
- `_es_cierre_valido()` exige la suma **exacta** de cuotas (`suma_cuotas == totalAmount`), no una tolerancia — así es como el calculador detecta el falso verde comparando contra lo que la API real dejó pasar.
- `closedAt` es un campo hipotético de trabajo: el modelo real de `SplitSession` (`services/social-split-api`) **no persiste hoy** un timestamp de cierre; ese campo lo aportaría el evento/outbox de cierre del issue #1/#4. `bank_kpis.py` es deliberadamente agnóstico de esa fuente y no la inventa.
- B-K2 y B-K3 son exposición/compromiso de una demo académica, nunca cobros reales ni pérdidas financieras.

## 5. Arquitectura y semántica temporal

### Contrato de eventos (estado actual, verificado contra el código)

`scripts/acceptance/resilience_checks.py` documenta el hallazgo de alcance verificado directamente contra el repositorio: **el único outbox que existe hoy es el de Payments -> Audit** (`services/payments-api/.../OutboxPublisher.java`, tabla `outbox_events`, publicado vía `POST` a `audit-api:/internal/events` con header `X-Event-Id`). `services/social-split-api` **no tiene** tabla de outbox, ni publicador, ni consumidor, ni ningún canal de eventos hacia Audit o hacia un dashboard en tiempo real. Por eso ninguno de los cinco casos de resiliencia (evento duplicado, eventos desordenados, broker caído con outbox pendiente, reinicio de consumidor con checkpoint, reconexión del dashboard) puede ejercitarse hoy contra Social Split: no hay `eventId` que duplicar, ni orden que alterar, ni outbox que quede pendiente, ni checkpoint de consumidor, ni canal de dashboard que reconectar. Ese contrato es trabajo de los issues **#1** (backend/outbox) y **#4** (tiempo real/dashboard).

### Temporizadores

- Ventana de cohorte de B-K1 y B-K2: 900 s (15 min).
- Edad mínima para que una sesión `OPEN` cuente en B-K3: 120 s.

### Qué significa "tiempo real" en este laboratorio

El objetivo de tiempo real del laboratorio es: **p95 ≤ 1 s** desde que se envía la operación a la API hasta que el panel representa la revisión, sobre **al menos 100 operaciones**, donde **una sola actualización perdida hace fallar la prueba completa**.

`scripts/acceptance/latency_benchmark.py` mide hoy, contra la API real y sin mocks, el tiempo de ida y vuelta de crear una sesión de Social Split (con un `hostMemberId` único como marcador) hasta confirmar que es visible vía `GET` (lectura-tras-escritura). El propio script declara que esto es "lo más cercano a tiempo real que se puede medir hoy con esta API sincrónica", porque el panel en vivo (Grafana Live / websocket, issue #3) todavía no existe. Aplica la regla dura de pérdidas: una actualización que nunca se confirma visible dentro del timeout **no se excluye** del cálculo de percentiles — se incluye con una latencia de penalización igual al timeout, y cualquier pérdida o error hace fallar la prueba completa (`exit 1`).

## 6. Diagrama del Release Gate

Estado real de `.github/workflows/ci.yml` hoy — el gate agregado **solo** exige que `architecture-contract` e `integration-test` (nombre del check: "Build, integration and observability") terminen en `success`; **no** ejecuta todavía la prueba de negocio ni las verificaciones de tiempo real (eso es trabajo del issue #4):

```text
PR
 |
 v
+------------------------+      +--------------------------+      +--------------------------+
| Architecture contract  |----->| Build, integration and   |----->|      Release gate        |
| (6 servicios, docs de  |      | observability             |      | (HOY: solo exige que     |
|  ownership, Compose/   |      | (build --wait, edge UI,   |      |  architecture-contract e |
|  observability config)  |      |  smoke-v2.sh, Prometheus/ |      |  integration-test ==     |
+------------------------+      |  Grafana health)          |      |  success)                |
                                 +--------------------------+      +--------------------------+
                                                                                |
                                                                                v
                                                                   +-------------------------+
                                                                   |  PASS  /  BLOCK         |
                                                                   |  (falla/omite/cancela   |
                                                                   |   cualquier etapa)      |
                                                                   +-------------------------+

PENDIENTE (issue #4): insertar aqui una etapa "Business Test" que ejecute
scripts/acceptance/run-acceptance.sh y tests/kpis, y que el Release gate
tambien dependa de su resultado. Hoy esa etapa NO existe en el pipeline
real; este bloque documenta el DISENO objetivo, no el estado actual.
```

Diagrama del pipeline objetivo del Deber 01 (diseño, no implementado todavía):

```text
PR -> Build -> Test -> Docker -> Business Test -> PASS/BLOCK
```

## 7. Evidencia: PR sano (verde)

`PENDIENTE — requiere abrir un PR de evidencia con la infraestructura sana y un cierre 60+40 de 100 que sí cumple la invariante (caso de fixtures/bankpulse/cierre-sano-60-40.json); depende de que #4 conecte scripts/acceptance/run-acceptance.sh al pipeline de CI (hoy el Release gate no lo invoca).`

| Campo | Valor |
|---|---|
| URL del PR | `PENDIENTE — Daniel debe pegar la URL real` |
| SHA del commit | `PENDIENTE — Daniel debe pegar el SHA real` |
| Run ID de GitHub Actions | `PENDIENTE — Daniel debe pegar el run id real` |
| `Architecture contract` | `PENDIENTE` |
| `Build, integration and observability` | `PENDIENTE` |
| `Release gate` | `PENDIENTE` |
| Salida de `bash scripts/acceptance/run-acceptance.sh` | `PENDIENTE — pegar la tabla resumen real de la corrida` |
| Captura del panel (Grafana Live) | `PENDIENTE — requiere el panel del issue #3, todavía no existe` |

## 8. Evidencia: PR con tecnología verde y negocio rojo

Esta es la regresión controlada del issue #5: infraestructura sana (API, DB y contenedores `UP`), pero el cierre `60 + 30` de un total `100` queda `COMPLETED` con un descuadre de `10.00` (caso `fixtures/bankpulse/cierre-descuadrado-60-30.json`). **Esta regresión se demuestra en un PR y nunca se integra en `main`.**

| Campo | Valor |
|---|---|
| URL del PR (draft, nunca mergeado) | `PENDIENTE — Daniel debe pegar la URL real` |
| SHA del commit | `PENDIENTE — Daniel debe pegar el SHA real` |
| Run ID de GitHub Actions | `PENDIENTE — Daniel debe pegar el run id real` |
| `Architecture contract` | `PENDIENTE (esperado: success — la regresión es de negocio, no de arquitectura)` |
| `Build, integration and observability` | `PENDIENTE (esperado: success — la infraestructura está sana)` |
| Resultado de `business_test_social_split.py` | `PENDIENTE (esperado: escenario_falso_verde=FAIL, con la línea "FALSO VERDE DETECTADO: HTTP 2xx + status COMPLETED + descuadre de 10.00 unidades")` |
| Resultado de `latency_benchmark.py` | `PENDIENTE` |
| Resultado de `resilience_checks.py` | `PENDIENTE (esperado hoy: SKIPPED, exit 3 — Social Split no tiene outbox propio, depende de #1/#4)` |
| Salida agregada de `run-acceptance.sh` | `PENDIENTE (esperado: RESULTADO GLOBAL: FAIL, exit 1, por el FAIL de negocio)` |

## 9. Evidencia del bloqueo efectivo del merge

`PENDIENTE — hoy el Release gate de .github/workflows/ci.yml (verificado en este repo) NO ejecuta business_test_social_split.py ni run-acceptance.sh; solo exige que architecture-contract e integration-test terminen en success. Por lo tanto, con el pipeline actual, el PR del punto 8 pasaría el gate agregado aunque el negocio esté en rojo — este es precisamente el vacío que el issue #4 debe cerrar incorporando una etapa de Business Test de la que dependa el Release gate. Esta fila queda PENDIENTE hasta que #4 la implemente y Daniel pueda evidenciar un bloqueo real.`

| Campo | Valor |
|---|---|
| ¿El Release gate hoy considera el resultado de negocio? | No (verificado en `.github/workflows/ci.yml`) |
| Etapa "Business Test" en el pipeline | `PENDIENTE — depende de #4` |
| Captura del check en rojo bloqueando el botón de merge | `PENDIENTE — depende de #4` |
| URL del PR bloqueado | `PENDIENTE` |

## 10. Diagnóstico y corrección

| Campo | Valor |
|---|---|
| Causa raíz del falso verde | Confirmada en el código: `SplitSession.closeIfAuthorized()` (`services/social-split-api/src/main/java/com/bankpulse/split/SplitSession.java`) valida únicamente `participants no vacíos` y `todos autorizados`; no compara `Σ shareAmount` contra `totalAmount`. |
| Corrección requerida | Issue #1 debe modificar `closeIfAuthorized()` para exigir `Σ shareAmount de autorizados == totalAmount` (con `BigDecimal`, comparación exacta) antes de permitir la transición a `COMPLETED`, y definir el código de error apropiado (4xx) para un cierre descuadrado. Además, issue #4 debe incorporar `scripts/acceptance/run-acceptance.sh` como etapa `Business Test` del pipeline y hacer que `Release gate` dependa de su resultado. |
| Estado de la corrección | `PENDIENTE — trabajo de #1 (dominio) y #4 (gate), no de #5` |
| Evidencia de la corrección aplicada | `PENDIENTE` |

## 11. Ejecución final verde

`PENDIENTE — requiere que #1 corrija closeIfAuthorized() y que #4 incorpore la etapa Business Test al gate (punto 10), para poder volver a correr scripts/acceptance/run-acceptance.sh y tests/kpis contra un despliegue sano donde el cierre descuadrado 60+30 sea rechazado con 4xx, y documentar aquí la corrida real.`

| Campo | Valor |
|---|---|
| URL del PR final | `PENDIENTE` |
| Run ID de GitHub Actions | `PENDIENTE` |
| Resultado de `business_test_social_split.py` | `PENDIENTE (esperado: RESULTADO: PASS, con escenario_falso_verde=PASS porque la API ahora rechaza el descuadre con 4xx y conserva OPEN)` |
| Resultado de `latency_benchmark.py` | `PENDIENTE (esperado: RESULTADO: PASS, p50/p95 reales, N>=100)` |
| Resultado de `run-acceptance.sh` | `PENDIENTE (esperado: RESULTADO GLOBAL: PASS, exit 0)` |
| `pytest tests/kpis` | `PENDIENTE (esperado: todos los casos en verde)` |

## 12. Cómo reproducir desde un Codespace limpio

Todos los comandos siguientes existen tal cual en este repositorio (`README.md`, `CONTRIBUTING.md`, `scripts/`).

**Bootstrap:**

```bash
cp .env.example .env
docker compose config
docker compose up -d --build --wait --wait-timeout 300
docker compose ps
bash scripts/smoke-v2.sh
```

**Observabilidad (Prometheus/Grafana/cAdvisor):**

```bash
docker compose -f observability/compose.yaml up -d
```

Grafana en el puerto `3000` (`admin / bankpulse_demo`), Prometheus en `9090`, cAdvisor en `8088`.

**Tráfico y evidencia de aceptación (issue #5):**

```bash
BANKPULSE_URL=http://localhost:8080 bash scripts/acceptance/run-acceptance.sh
```

Este orquestador ejecuta en orden `business_test_social_split.py`, `latency_benchmark.py` y `resilience_checks.py`, e imprime una tabla resumen con el código de salida real de cada etapa (`0`=PASS, `1`=FAIL, `2`=ERROR, `3`=SKIPPED).

Para ejecutar cada etapa por separado con parámetros propios (ver `--help` de cada script):

```bash
python3 scripts/acceptance/business_test_social_split.py --base-url http://localhost:8080
python3 scripts/acceptance/latency_benchmark.py --base-url http://localhost:8080
python3 scripts/acceptance/resilience_checks.py --base-url http://localhost:8080
```

**Replay del caso de aceptación exacto del issue #5** (cierre descuadrado `60 + 30` de un total `100`, se puede repetir contra un entorno recién levantado):

```bash
split_id=$(curl -fsS -X POST http://localhost:8080/api/splits \
  -H 'Content-Type: application/json' \
  -d '{"hostMemberId":"MEMBER-BIZ-FALSO-VERDE","totalAmount":100.00,"currency":"USD"}' \
  | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')

p1=$(curl -fsS -X POST "http://localhost:8080/api/splits/$split_id/participants" \
  -H 'Content-Type: application/json' -d '{"memberId":"MEMBER-A","shareAmount":60.00}' \
  | sed -n 's/.*"id":"\([^"]*\)".*/\1/p' | head -1)
p2=$(curl -fsS -X POST "http://localhost:8080/api/splits/$split_id/participants" \
  -H 'Content-Type: application/json' -d '{"memberId":"MEMBER-B","shareAmount":30.00}' \
  | sed -n 's/.*"id":"\([^"]*\)".*/\1/p' | tail -1)

curl -fsS -X POST "http://localhost:8080/api/splits/$split_id/participants/$p1/authorize" \
  -H 'Content-Type: application/json' -d '{"paymentReference":"PAY-REF-1"}'
curl -fsS -X POST "http://localhost:8080/api/splits/$split_id/participants/$p2/authorize" \
  -H 'Content-Type: application/json' -d '{"paymentReference":"PAY-REF-2"}'

curl -isS -X POST "http://localhost:8080/api/splits/$split_id/close"
curl -fsS "http://localhost:8080/api/splits/$split_id"
```

**Pruebas de KPIs (deterministas, sin infraestructura):**

```bash
pip install -r requirements-test.txt
python3 -m pytest tests/kpis -v
```

**Reinicio limpio del stack:**

```bash
docker compose -f observability/compose.yaml down
docker compose down
```

**Live / panel de Grafana:** `PENDIENTE — depende de que el issue #3 (Grafana Live, paneles y alertas) exista; hoy no hay panel ni dashboard de streaming que reproducir en este repositorio.`

## 13. Tabla de contribuciones del equipo

| Issue | Responsable | Entrega (según `CONTRIBUTING.md`) | PR | Evidencia |
|---|---|---|---|---|
| #1 | `@nikotov` | Contrato de eventos, outbox de Social Split y definición de KPIs propios | `PENDIENTE` | `PENDIENTE` |
| #2 | `@DanielSalazar0710` | Analítica continua, deduplicación, estado persistente y temporizadores | `PENDIENTE` | `PENDIENTE` |
| #3 | `@oandretty010` | Grafana Live, paneles, alertas y reconexión | `PENDIENTE` | `PENDIENTE` |
| #4 | `@VillaforTech` | Compose, Redpanda, integración y Release Gate del deber | `PENDIENTE` | `PENDIENTE` |
| #5 | `@Dmt-155lbs` (Daniel, autor de este documento) | Pruebas de extremo a extremo, resiliencia y evidencia del falso verde | `PENDIENTE` | `scripts/acceptance/`, `tests/kpis/`, `fixtures/bankpulse/` en `feat/5-deber-01-harness`; ejecución real `PENDIENTE` |

## 14. Checklist de la rúbrica 3+5+2

**Bloque de 3 (fundamentos del falso verde):**

- [ ] Capacidad de negocio identificada correctamente (Sección 1) — hecho en este documento
- [ ] Escenario de falso verde descrito con precisión técnica, incluyendo la causa raíz en el código (Sección 2) — hecho en este documento
- [ ] KPIs propios con fórmula, población, ventana y umbral (Sección 4) — hecho en este documento

**Bloque de 5 (evidencia de extremo a extremo):**

- [ ] PR sano documentado con checks reales — `PENDIENTE` (Sección 7)
- [ ] PR con regresión de negocio (tecnología verde, negocio rojo) — `PENDIENTE` (Sección 8)
- [ ] Bloqueo efectivo del merge evidenciado — `PENDIENTE`, depende de #4 (Sección 9)
- [ ] Diagnóstico y corrección documentados — `PENDIENTE`, corrección es de #1/#4 (Sección 10)
- [ ] Ejecución final verde evidenciada — `PENDIENTE` (Sección 11)

**Bloque de 2 (reproducibilidad y rigor):**

- [ ] Instrucciones de reproducción desde Codespace limpio con comandos reales verificados contra el repo — hecho en este documento (Sección 12)
- [ ] Distinción explícita entre diseño/esperado y observado, sin inventar URLs/SHAs/run ids/capturas/latencias — hecho en este documento

## 15. Límites del benchmark de laboratorio

- Los montos son unidades monetarias de laboratorio (datos demo). No son USD, no son ingresos reales ni una pérdida financiera demostrada; BankPulse es un laboratorio y ninguna sesión mueve dinero real.
- El benchmark de latencia (`latency_benchmark.py`) mide hoy solo la ida y vuelta de crear una sesión y confirmarla visible vía `GET` (lectura-tras-escritura), no hasta un panel en vivo — porque ese panel (issue #3) todavía no existe. El propio script lo declara como la aproximación más cercana posible con esta API sincrónica.
- Los cinco casos de `resilience_checks.py` (evento duplicado, eventos desordenados, broker caído con outbox pendiente, reinicio de consumidor con checkpoint, reconexión de dashboard) son estructuralmente imposibles de ejecutar hoy contra Social Split: no existe ningún outbox, publicador, consumidor ni canal de eventos para este dominio (el único outbox real del repo es Payments -> Audit). El script lo detecta en vivo (no lo asume) y reporta `SKIPPED` (exit 3), que el orquestador nunca cuenta como verde.
- El Release gate actual (`.github/workflows/ci.yml`) solo exige que `Architecture contract` y `Build, integration and observability` terminen en `success`; no ejecuta la prueba de negocio del Deber 01. Incorporar esa etapa es trabajo del issue #4, no de este documento ni del issue #5.
- El fallo de CI observado el 9 de septiembre de 2026 al configurar el equipo fue en el smoke de idempotencia de pagos (según `CONTRIBUTING.md`), una caída técnica de infraestructura/regresión previa y **no** es el falso verde de negocio de Social Split que este documento analiza.
- Los umbrales de los KPIs (B-K1 = 100 %, B-K2 = 0, B-K3 = 0) son metas de laboratorio para un ejercicio académico, no un SLA de producción.
