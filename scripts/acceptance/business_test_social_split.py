#!/usr/bin/env python3
"""Prueba de ACEPTACION DE NEGOCIO para Social Split (issue #5).

Objetivo: verificar de extremo a extremo (API real, sin mocks) que el
sistema no reporta "verde" (HTTP 2xx + status COMPLETED) cuando la
capacidad protegida del negocio ("las cuotas autorizadas deben sumar
exactamente el total") esta violada. Esta es la prueba que detecta el
FALSO VERDE descrito en el issue #5: hoy `closeIfAuthorized()` en
`SplitSession` solo valida que existan participantes y que todos esten
autorizados; NO valida que la suma de cuotas sea igual a `totalAmount`.
Esta prueba NO corrige ese defecto (eso es trabajo del issue #1): solo lo
detecta y falla con evidencia clara.

Solo usa la biblioteca estandar de Python (urllib.request, json, time,
argparse). No requiere `requests` ni ninguna dependencia externa.

Codigos de salida:
  0 -> PASS: todos los escenarios de negocio se comportaron como se espera
       (incluyendo que el falso verde fue detectado y por tanto NO paso).
  1 -> FAIL de negocio: algun escenario violo la capacidad protegida
       (incluye el caso en el que la API deja pasar el descuadre).
  2 -> ERROR de entorno: la API no llego a estar lista (readiness), o hubo
       un error de red/infra que impide siquiera ejercitar los escenarios.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from decimal import Decimal

DEFAULT_BASE_URL = "http://localhost:8080"
HEALTH_PATHS = ("/health/social-split",)
READINESS_TIMEOUT_S = 60
READINESS_POLL_S = 2


@dataclass
class ResultadoEscenario:
    nombre: str
    ok: bool
    detalle: str


@dataclass
class ResumenNegocio:
    resultados: list[ResultadoEscenario] = field(default_factory=list)

    def agregar(self, nombre: str, ok: bool, detalle: str) -> None:
        self.resultados.append(ResultadoEscenario(nombre, ok, detalle))

    @property
    def todo_ok(self) -> bool:
        return all(r.ok for r in self.resultados)

    def imprimir_linea_final(self) -> None:
        partes = []
        for r in self.resultados:
            estado = "PASS" if r.ok else "FAIL"
            partes.append(f"{r.nombre}={estado}")
        print("RESUMEN NEGOCIO: " + " | ".join(partes))


class ErrorDeEntorno(RuntimeError):
    """Se lanza cuando la API no esta lista o hay un fallo de infraestructura."""


def _http(method: str, url: str, body: dict | None = None, timeout: float = 10.0):
    """Hace una llamada HTTP con la stdlib. Devuelve (status_code, dict|None).

    No lanza excepcion por status >= 400: los codigos de error son parte del
    protocolo de negocio que estamos verificando (p.ej. 4xx = rechazo
    correcto de un cierre invalido).
    """
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
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
            parsed = {"raw": raw.decode("utf-8", errors="replace")}
        return exc.code, parsed
    except urllib.error.URLError as exc:
        raise ErrorDeEntorno(f"No se pudo conectar a {url}: {exc}") from exc


def esperar_readiness(base_url: str, timeout_s: int = READINESS_TIMEOUT_S) -> None:
    """Espera a que /health/social-split responda UP. Lanza ErrorDeEntorno si
    se agota el tiempo. Esto es readiness REAL contra la API, no un sleep fijo.
    """
    limite = time.monotonic() + timeout_s
    ultimo_error = None
    while time.monotonic() < limite:
        try:
            status, body = _http("GET", base_url + "/health/social-split")
            if status == 200 and body is not None:
                estado = body.get("status") if isinstance(body, dict) else None
                if estado == "UP":
                    return
                ultimo_error = f"status HTTP 200 pero cuerpo no UP: {body}"
            else:
                ultimo_error = f"status HTTP {status}"
        except ErrorDeEntorno as exc:
            ultimo_error = str(exc)
        time.sleep(READINESS_POLL_S)
    raise ErrorDeEntorno(
        f"Timeout de {timeout_s}s esperando readiness de social-split. Ultimo error: {ultimo_error}"
    )


def _crear_split(base_url: str, host_member_id: str, total: str, currency: str = "USD") -> dict:
    status, body = _http(
        "POST",
        f"{base_url}/api/splits",
        {"hostMemberId": host_member_id, "totalAmount": total, "currency": currency},
    )
    if status != 201 or not isinstance(body, dict):
        raise ErrorDeEntorno(f"No se pudo crear split (status={status}, body={body})")
    return body


def _agregar_participante(base_url: str, split_id: str, member_id: str, share: str) -> dict:
    status, body = _http(
        "POST",
        f"{base_url}/api/splits/{split_id}/participants",
        {"memberId": member_id, "shareAmount": share},
    )
    if status != 200 or not isinstance(body, dict):
        raise ErrorDeEntorno(f"No se pudo agregar participante (status={status}, body={body})")
    return body


def _autorizar(base_url: str, split_id: str, participant_id: str, payment_reference: str) -> tuple[int, dict | None]:
    return _http(
        "POST",
        f"{base_url}/api/splits/{split_id}/participants/{participant_id}/authorize",
        {"paymentReference": payment_reference},
    )


def _cerrar(base_url: str, split_id: str) -> tuple[int, dict | None]:
    return _http("POST", f"{base_url}/api/splits/{split_id}/close")


def _obtener(base_url: str, split_id: str) -> dict:
    status, body = _http("GET", f"{base_url}/api/splits/{split_id}")
    if status != 200 or not isinstance(body, dict):
        raise ErrorDeEntorno(f"No se pudo leer split (status={status}, body={body})")
    return body


def _participant_ids(sesion: dict) -> list[str]:
    return [p["id"] for p in sesion.get("participants", [])]


def escenario_caso_sano(base_url: str, resumen: ResumenNegocio) -> None:
    """a) CASO SANO: total 100, cuotas 60 y 40, ambos autorizados, close ->
    debe quedar COMPLETED."""
    nombre = "caso_sano_60_40_de_100"
    try:
        sesion = _crear_split(base_url, "MEMBER-BIZ-SANO", "100.00")
        split_id = sesion["id"]
        sesion = _agregar_participante(base_url, split_id, "MEMBER-A", "60.00")
        sesion = _agregar_participante(base_url, split_id, "MEMBER-B", "40.00")
        pids = _participant_ids(sesion)
        for i, pid in enumerate(pids):
            status, _ = _autorizar(base_url, split_id, pid, f"PAY-REF-SANO-{i}")
            if status != 200:
                resumen.agregar(nombre, False, f"autorizar participante {pid} devolvio {status}")
                return
        status, body = _cerrar(base_url, split_id)
        final = _obtener(base_url, split_id)
        if status in (200, 201) and final.get("status") == "COMPLETED":
            resumen.agregar(nombre, True, "cierre sano quedo COMPLETED como se esperaba")
        else:
            resumen.agregar(
                nombre,
                False,
                f"cierre sano NO quedo COMPLETED (status HTTP close={status}, estado final={final.get('status')})",
            )
    except ErrorDeEntorno:
        raise
    except Exception as exc:  # noqa: BLE001 - queremos reportar cualquier fallo de negocio, no solo los previstos
        resumen.agregar(nombre, False, f"excepcion inesperada: {exc}")


def escenario_falso_verde(base_url: str, resumen: ResumenNegocio) -> None:
    """b) CASO FALSO VERDE: total 100, cuotas 60 y 30 (descuadre de 10),
    ambos autorizados, close.

    La prueba de NEGOCIO debe FALLAR si la API responde 2xx y deja
    COMPLETED, porque ese descuadre es una violacion de la capacidad
    protegida (el total prometido a los participantes no coincide con lo
    que realmente se autorizo). Si en cambio la API rechaza el cierre con
    4xx y conserva OPEN, ese es el comportamiento correcto -> PASS.
    """
    nombre = "caso_falso_verde_60_30_de_100"
    try:
        sesion = _crear_split(base_url, "MEMBER-BIZ-FALSO-VERDE", "100.00")
        split_id = sesion["id"]
        sesion = _agregar_participante(base_url, split_id, "MEMBER-A", "60.00")
        sesion = _agregar_participante(base_url, split_id, "MEMBER-B", "30.00")
        pids = _participant_ids(sesion)
        for i, pid in enumerate(pids):
            status, _ = _autorizar(base_url, split_id, pid, f"PAY-REF-DESCUADRE-{i}")
            if status != 200:
                resumen.agregar(nombre, False, f"autorizar participante {pid} devolvio {status}")
                return

        status_close, _ = _cerrar(base_url, split_id)
        final = _obtener(base_url, split_id)
        descuadre = Decimal(str(final.get("totalAmount", "0"))) - Decimal("90.00")

        if 200 <= status_close < 300 and final.get("status") == "COMPLETED":
            print(
                "FALSO VERDE DETECTADO: HTTP "
                f"{status_close} + status COMPLETED + descuadre de {descuadre} unidades"
            )
            resumen.agregar(
                nombre,
                False,
                f"la API dejo cerrar (HTTP {status_close}, status={final.get('status')}) "
                f"una sesion con descuadre de {descuadre}; la capacidad protegida NO se respeto",
            )
        elif status_close >= 400 and final.get("status") == "OPEN":
            resumen.agregar(
                nombre,
                True,
                f"la API rechazo correctamente el cierre descuadrado (HTTP {status_close}, sigue OPEN)",
            )
        else:
            resumen.agregar(
                nombre,
                False,
                f"resultado ambiguo/inesperado: HTTP close={status_close}, estado final={final.get('status')}",
            )
    except ErrorDeEntorno:
        raise
    except Exception as exc:  # noqa: BLE001
        resumen.agregar(nombre, False, f"excepcion inesperada: {exc}")


def escenario_sin_consentimiento(base_url: str, resumen: ResumenNegocio) -> None:
    """c) CASO SIN CONSENTIMIENTO: un participante sin autorizar -> el cierre
    debe ser rechazado."""
    nombre = "caso_sin_consentimiento"
    try:
        sesion = _crear_split(base_url, "MEMBER-BIZ-SIN-CONSENTIMIENTO", "100.00")
        split_id = sesion["id"]
        sesion = _agregar_participante(base_url, split_id, "MEMBER-A", "60.00")
        sesion = _agregar_participante(base_url, split_id, "MEMBER-B", "40.00")
        pids = _participant_ids(sesion)
        # Solo autorizamos al primero; el segundo queda sin consentimiento.
        status, _ = _autorizar(base_url, split_id, pids[0], "PAY-REF-PARCIAL")
        if status != 200:
            resumen.agregar(nombre, False, f"autorizar el primer participante devolvio {status}")
            return

        status_close, _ = _cerrar(base_url, split_id)
        final = _obtener(base_url, split_id)
        if status_close >= 400 and final.get("status") == "OPEN":
            resumen.agregar(
                nombre, True, f"cierre sin consentimiento total fue rechazado (HTTP {status_close})"
            )
        else:
            resumen.agregar(
                nombre,
                False,
                f"cierre sin consentimiento NO fue rechazado (HTTP {status_close}, estado={final.get('status')})",
            )
    except ErrorDeEntorno:
        raise
    except Exception as exc:  # noqa: BLE001
        resumen.agregar(nombre, False, f"excepcion inesperada: {exc}")


def escenario_cierre_repetido(base_url: str, resumen: ResumenNegocio) -> None:
    """d) CIERRE REPETIDO: cerrar dos veces no debe producir efectos
    adicionales (la sesion debe seguir COMPLETED y no duplicar nada)."""
    nombre = "caso_cierre_repetido"
    try:
        sesion = _crear_split(base_url, "MEMBER-BIZ-REPETIDO", "100.00")
        split_id = sesion["id"]
        sesion = _agregar_participante(base_url, split_id, "MEMBER-A", "60.00")
        sesion = _agregar_participante(base_url, split_id, "MEMBER-B", "40.00")
        pids = _participant_ids(sesion)
        for i, pid in enumerate(pids):
            status, _ = _autorizar(base_url, split_id, pid, f"PAY-REF-REPETIDO-{i}")
            if status != 200:
                resumen.agregar(nombre, False, f"autorizar participante {pid} devolvio {status}")
                return

        status_1, _ = _cerrar(base_url, split_id)
        estado_tras_primer_cierre = _obtener(base_url, split_id)
        if status_1 not in (200, 201) or estado_tras_primer_cierre.get("status") != "COMPLETED":
            resumen.agregar(
                nombre,
                False,
                f"el primer cierre no dejo COMPLETED (HTTP {status_1}, estado={estado_tras_primer_cierre.get('status')})",
            )
            return

        participantes_tras_primer_cierre = estado_tras_primer_cierre.get("participants", [])

        # Segundo cierre: no debe cambiar el estado ni los participantes.
        status_2, _ = _cerrar(base_url, split_id)
        estado_tras_segundo_cierre = _obtener(base_url, split_id)
        participantes_tras_segundo_cierre = estado_tras_segundo_cierre.get("participants", [])

        sigue_completed = estado_tras_segundo_cierre.get("status") == "COMPLETED"
        sin_participantes_extra = len(participantes_tras_segundo_cierre) == len(participantes_tras_primer_cierre)
        # Un segundo cierre "sin efecto" puede responder 2xx (idempotente/no-op)
        # o 4xx (rechazado por ya estar cerrado); ambos son aceptables siempre
        # que el estado no cambie ni se dupliquen participantes.
        if sigue_completed and sin_participantes_extra:
            resumen.agregar(
                nombre,
                True,
                f"segundo cierre no produjo efectos adicionales (HTTP={status_2}, sigue COMPLETED, "
                f"participantes={len(participantes_tras_segundo_cierre)})",
            )
        else:
            resumen.agregar(
                nombre,
                False,
                f"segundo cierre produjo efectos adicionales (HTTP={status_2}, "
                f"estado={estado_tras_segundo_cierre.get('status')}, "
                f"participantes antes={len(participantes_tras_primer_cierre)} "
                f"despues={len(participantes_tras_segundo_cierre)})",
            )
    except ErrorDeEntorno:
        raise
    except Exception as exc:  # noqa: BLE001
        resumen.agregar(nombre, False, f"excepcion inesperada: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL del edge (default: %(default)s)")
    parser.add_argument(
        "--readiness-timeout",
        type=int,
        default=READINESS_TIMEOUT_S,
        help="Segundos maximos a esperar por readiness (default: %(default)s)",
    )
    args = parser.parse_args()

    print(f"[readiness] esperando /health/social-split en {args.base_url} ...")
    try:
        esperar_readiness(args.base_url, args.readiness_timeout)
    except ErrorDeEntorno as exc:
        print(f"ERROR DE ENTORNO: {exc}", file=sys.stderr)
        return 2
    print("[readiness] OK")

    resumen = ResumenNegocio()
    try:
        escenario_caso_sano(args.base_url, resumen)
        escenario_falso_verde(args.base_url, resumen)
        escenario_sin_consentimiento(args.base_url, resumen)
        escenario_cierre_repetido(args.base_url, resumen)
    except ErrorDeEntorno as exc:
        print(f"ERROR DE ENTORNO durante la ejecucion: {exc}", file=sys.stderr)
        resumen.imprimir_linea_final()
        return 2

    for r in resumen.resultados:
        estado = "PASS" if r.ok else "FAIL"
        print(f"[{estado}] {r.nombre}: {r.detalle}")

    resumen.imprimir_linea_final()

    if resumen.todo_ok:
        print("RESULTADO: PASS (comportamiento de negocio correcto en todos los escenarios)")
        return 0
    print("RESULTADO: FAIL (al menos un escenario de negocio viola la capacidad protegida)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
