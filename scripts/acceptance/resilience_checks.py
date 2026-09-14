#!/usr/bin/env python3
"""Chequeos de resiliencia de "tiempo real" para Social Split (issue #5).

Casos que este esqueleto DEBE cubrir cuando el contrato exista:
  1. mismo eventId duplicado (el consumidor debe deduplicar)
  2. eventos desordenados (llegan fuera de secuencia)
  3. broker caido con el cambio ya confirmado en la API y el evento
     pendiente en el outbox (debe seguir pendiente, no perderse)
  4. reinicio del consumidor antes/despues del checkpoint (no debe
     duplicar ni perder eventos ya confirmados)
  5. reconexion del dashboard (debe resincronizar sin duplicar ni perder
     actualizaciones)

HALLAZGO DE ALCANCE (verificado contra el codigo, no supuesto): el unico
outbox que existe hoy en el repo es el de Payments -> Audit
(`services/payments-api/.../OutboxPublisher.java`, tabla `outbox_events`,
publicado via POST a `audit-api:/internal/events` con header
`X-Event-Id`). Social Split (`services/social-split-api`) NO tiene tabla de
outbox, ni publicador, ni consumidor, ni ningun canal de eventos hacia
Audit o hacia un dashboard en tiempo real. Por lo tanto NINGUNO de los 5
casos de arriba puede ejercitarse hoy contra Social Split: no hay eventId
que duplicar, ni orden que alterar, ni outbox que quede pendiente, ni
checkpoint de consumidor, ni canal de dashboard que reconectar.

Ese contrato (outbox de Social Split + consumidor + canal en tiempo real)
es trabajo de los issues #1 (backend/outbox) y #4 (tiempo real/dashboard).
Este script:
  - PRUEBA en vivo (contra la API real) que el contrato sigue ausente, en
    vez de asumirlo a ciegas, para no quedar obsoleto en silencio el dia
    que alguien lo construya.
  - Si el contrato sigue ausente: reporta explicitamente
    "SKIPPED: requiere #1/#4" por cada caso, con exit 3. SKIPPED nunca es
    exit 0: esta PROHIBIDO que este script reporte verde por una
    dependencia ausente.
  - Si el contrato ya existe (alguien completo #1/#4): cada caso trae un
    TODO preciso de lo que hay que implementar para ejercitarlo de verdad;
    hasta que se implemente, seguira marcando SKIPPED en vez de asumir que
    "existir" implica "funcionar".

Solo usa la biblioteca estandar (urllib.request, json, time, argparse).

Codigos de salida:
  0 -> PASS: todos los casos se ejecutaron y pasaron de verdad.
  1 -> FAIL: el contrato existe pero algun caso de resiliencia fallo.
  2 -> ERROR de entorno: la API no llego a estar lista (readiness).
  3 -> SKIPPED: al menos un caso se salto por falta del contrato
       (issue #1/#4). Nunca se cuenta como verde.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_READINESS_TIMEOUT_S = 60
READINESS_POLL_S = 2
MENSAJE_SKIP = "SKIPPED: requiere #1/#4"


class ErrorDeEntorno(RuntimeError):
    pass


@dataclass
class ResultadoCaso:
    nombre: str
    estado: str  # "PASS" | "FAIL" | "SKIPPED"
    detalle: str


def _http(method: str, url: str, timeout: float = 10.0):
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            parsed = json.loads(raw) if raw else None
            return resp.status, parsed
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = None
        return exc.code, parsed


def esperar_readiness(base_url: str, timeout_s: int) -> None:
    limite = time.monotonic() + timeout_s
    ultimo_error = None
    while time.monotonic() < limite:
        try:
            status, body = _http("GET", base_url + "/health/social-split", timeout=5.0)
            if status == 200 and isinstance(body, dict) and body.get("status") == "UP":
                return
            ultimo_error = f"status HTTP {status}, body={body}"
        except urllib.error.URLError as exc:
            ultimo_error = str(exc)
        time.sleep(READINESS_POLL_S)
    raise ErrorDeEntorno(f"Timeout de {timeout_s}s esperando readiness. Ultimo error: {ultimo_error}")


def _contrato_outbox_social_split_existe(base_url: str) -> tuple[bool, str]:
    """Prueba EN VIVO si existe algun contrato de eventos para Social Split
    analogo al de Payments (`/api/outbox`, `X-Event-Id`, tipos de evento en
    Audit). Devuelve (existe, detalle_de_la_prueba).

    No asume nada: hace las llamadas reales y decide segun la respuesta.
    """
    detalles = []

    # 1) Existe un endpoint de outbox propio de social-split, como
    #    /api/outbox lo es para payments?
    try:
        status, _ = _http("GET", f"{base_url}/api/splits/outbox", timeout=5.0)
        detalles.append(f"GET /api/splits/outbox -> {status}")
        if status == 200:
            return True, "; ".join(detalles) + " (existe endpoint de outbox para social-split)"
    except urllib.error.URLError as exc:
        detalles.append(f"GET /api/splits/outbox -> error de red: {exc}")

    # 2) El feed de auditoria ya contiene algun tipo de evento de Social
    #    Split (p.ej. SPLIT_CLOSED / SPLIT_COMPLETED / SOCIAL_SPLIT_*)?
    try:
        status, body = _http("GET", f"{base_url}/api/audit", timeout=5.0)
        detalles.append(f"GET /api/audit -> {status}")
        if status == 200:
            texto = json.dumps(body) if body is not None else ""
            if any(marca in texto for marca in ("SPLIT_", "SOCIAL_SPLIT")):
                return True, "; ".join(detalles) + " (audit ya contiene eventos de social-split)"
    except urllib.error.URLError as exc:
        detalles.append(f"GET /api/audit -> error de red: {exc}")

    return False, "; ".join(detalles) + " (ningun endpoint/evento de outbox propio de social-split)"


def caso_1_evento_duplicado(base_url: str, contrato_existe: bool, detalle_probe: str) -> ResultadoCaso:
    nombre = "1_mismo_eventId_duplicado"
    if not contrato_existe:
        print(f"[{nombre}] {MENSAJE_SKIP} ({detalle_probe})")
        return ResultadoCaso(
            nombre,
            "SKIPPED",
            f"{MENSAJE_SKIP}: no existe un eventId/outbox de Social Split que deduplicar. {detalle_probe}",
        )
    # TODO(issue #1/#4): cuando exista el outbox de Social Split, publicar
    # el MISMO eventId dos veces hacia el consumidor (o reenviar el mismo
    # X-Event-Id via el publicador real) y verificar que:
    #   - el efecto de negocio ocurre UNA sola vez (no se duplica el cierre
    #     ni el registro de auditoria correspondiente), y
    #   - el segundo envio se reporta explicitamente como duplicado
    #     detectado (no como un exito silencioso indistinguible del primero).
    return ResultadoCaso(nombre, "SKIPPED", f"{MENSAJE_SKIP}: TODO pendiente de implementar contra el contrato real")


def caso_2_eventos_desordenados(base_url: str, contrato_existe: bool, detalle_probe: str) -> ResultadoCaso:
    nombre = "2_eventos_desordenados"
    if not contrato_existe:
        print(f"[{nombre}] {MENSAJE_SKIP} ({detalle_probe})")
        return ResultadoCaso(
            nombre,
            "SKIPPED",
            f"{MENSAJE_SKIP}: no hay canal de eventos de Social Split donde el orden pueda alterarse. {detalle_probe}",
        )
    # TODO(issue #1/#4): entregar al consumidor un evento "posterior"
    # (p.ej. SPLIT_COMPLETED) antes que su evento "anterior" correspondiente
    # (p.ej. PARTICIPANT_AUTHORIZED) y verificar que el estado final
    # converge al correcto (por timestamp/version, no por orden de llegada),
    # en vez de dejar al sistema en un estado inconsistente.
    return ResultadoCaso(nombre, "SKIPPED", f"{MENSAJE_SKIP}: TODO pendiente de implementar contra el contrato real")


def caso_3_broker_caido_outbox_pendiente(base_url: str, contrato_existe: bool, detalle_probe: str) -> ResultadoCaso:
    nombre = "3_broker_caido_outbox_pendiente"
    if not contrato_existe:
        print(f"[{nombre}] {MENSAJE_SKIP} ({detalle_probe})")
        return ResultadoCaso(
            nombre,
            "SKIPPED",
            f"{MENSAJE_SKIP}: Social Split no tiene outbox propio; ademas compose.yaml no declara ningun "
            f"broker de mensajeria (solo mariadb/mongo/postgres/redis) que se pueda tumbar. {detalle_probe}",
        )
    # TODO(issue #1/#4): con el broker/canal de publicacion caido, confirmar
    # un cambio en la API (p.ej. cerrar una sesion sana) y verificar que:
    #   - la API responde 2xx igual (el cambio de negocio ya esta commiteado
    #     en su propia base de datos), y
    #   - el evento correspondiente queda pendiente en el outbox de Social
    #     Split (published=false), NUNCA se pierde ni se marca publicado
    #     falsamente, hasta que el broker vuelva.
    return ResultadoCaso(nombre, "SKIPPED", f"{MENSAJE_SKIP}: TODO pendiente de implementar contra el contrato real")


def caso_4_reinicio_consumidor_checkpoint(base_url: str, contrato_existe: bool, detalle_probe: str) -> ResultadoCaso:
    nombre = "4_reinicio_consumidor_antes_despues_checkpoint"
    if not contrato_existe:
        print(f"[{nombre}] {MENSAJE_SKIP} ({detalle_probe})")
        return ResultadoCaso(
            nombre,
            "SKIPPED",
            f"{MENSAJE_SKIP}: no existe un consumidor de eventos de Social Split cuyo checkpoint probar. {detalle_probe}",
        )
    # TODO(issue #1/#4): reiniciar el proceso consumidor (a) justo ANTES de
    # que confirme el checkpoint de un evento ya procesado, y (b) justo
    # DESPUES. Verificar en ambos casos que, tras el reinicio, el evento se
    # procesa EXACTAMENTE una vez desde el punto de vista de negocio (usar
    # el mismo mecanismo de deduplicacion por eventId del caso 1), sin
    # perder eventos posteriores en la cola.
    return ResultadoCaso(nombre, "SKIPPED", f"{MENSAJE_SKIP}: TODO pendiente de implementar contra el contrato real")


def caso_5_reconexion_dashboard(base_url: str, contrato_existe: bool, detalle_probe: str) -> ResultadoCaso:
    nombre = "5_reconexion_dashboard"
    if not contrato_existe:
        print(f"[{nombre}] {MENSAJE_SKIP} ({detalle_probe})")
        return ResultadoCaso(
            nombre,
            "SKIPPED",
            f"{MENSAJE_SKIP}: no existe ningun canal en tiempo real (websocket/SSE/Grafana Live) hacia un "
            f"dashboard para Social Split que se pueda desconectar y reconectar. {detalle_probe}",
        )
    # TODO(issue #1/#4): abrir la conexion en tiempo real del dashboard,
    # forzar una desconexion mientras ocurren cambios de negocio, y al
    # reconectar verificar que el dashboard resincroniza el estado completo
    # (sin duplicar eventos ya vistos ni perder los ocurridos durante el
    # corte).
    return ResultadoCaso(nombre, "SKIPPED", f"{MENSAJE_SKIP}: TODO pendiente de implementar contra el contrato real")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--readiness-timeout", type=int, default=DEFAULT_READINESS_TIMEOUT_S)
    args = parser.parse_args()

    print(f"[readiness] esperando /health/social-split en {args.base_url} ...")
    try:
        esperar_readiness(args.base_url, args.readiness_timeout)
    except ErrorDeEntorno as exc:
        print(f"ERROR DE ENTORNO: {exc}", file=sys.stderr)
        return 2
    print("[readiness] OK")

    try:
        contrato_existe, detalle_probe = _contrato_outbox_social_split_existe(args.base_url)
    except urllib.error.URLError as exc:
        print(f"ERROR DE ENTORNO durante la prueba del contrato: {exc}", file=sys.stderr)
        return 2

    print(f"[contrato outbox social-split] existe={contrato_existe} ({detalle_probe})")

    resultados = [
        caso_1_evento_duplicado(args.base_url, contrato_existe, detalle_probe),
        caso_2_eventos_desordenados(args.base_url, contrato_existe, detalle_probe),
        caso_3_broker_caido_outbox_pendiente(args.base_url, contrato_existe, detalle_probe),
        caso_4_reinicio_consumidor_checkpoint(args.base_url, contrato_existe, detalle_probe),
        caso_5_reconexion_dashboard(args.base_url, contrato_existe, detalle_probe),
    ]

    print("RESUMEN RESILIENCIA: " + " | ".join(f"{r.nombre}={r.estado}" for r in resultados))
    for r in resultados:
        print(f"  - [{r.estado}] {r.nombre}: {r.detalle}")

    if any(r.estado == "FAIL" for r in resultados):
        print("RESULTADO: FAIL (el contrato existe pero algun caso de resiliencia no se cumplio)")
        return 1
    if any(r.estado == "SKIPPED" for r in resultados):
        print(
            "RESULTADO: SKIPPED (ningun caso puede ejercitarse hoy sin el outbox/consumidor/canal de "
            "tiempo real de Social Split; NO cuenta como verde -- ver issue #1/#4)"
        )
        return 3
    print("RESULTADO: PASS (todos los casos de resiliencia se ejecutaron y pasaron)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
