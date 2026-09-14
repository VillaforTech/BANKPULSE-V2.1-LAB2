#!/usr/bin/env python3
"""Benchmark de latencia de "tiempo real" para Social Split (issue #5).

Mide, contra la API real (sin mocks), el tiempo de ida-y-vuelta de al menos
N operaciones identificables: cada una crea una sesion de Social Split con
un `hostMemberId` unico (el "marcador") y luego confirma que la sesion es
visible via GET (lectura-tras-escritura). Eso es lo mas cercano a "tiempo
real" que se puede medir hoy con esta API sincronica; NO mide un panel en
vivo porque ese panel (Grafana Live / websocket del dashboard) todavia no
existe en este repo.

Solo usa la biblioteca estandar (urllib.request, json, time, argparse). No
requiere `requests` ni ninguna dependencia externa.

REGLA DURA: una actualizacion "perdida" (nunca se pudo confirmar que la
sesion se volvio visible dentro del timeout) NO se excluye del calculo de
percentiles: se incluye con una latencia de penalizacion igual al timeout
configurado. Excluirla inflaria artificialmente los resultados y ocultaria
el problema. Ademas, cualquier perdida o error hace FALLAR la prueba
(exit 1): un benchmark de latencia que solo reporta numeros y nunca falla
es otro tipo de falso verde.

Codigos de salida:
  0 -> PASS: N operaciones enviadas, todas vistas, sin errores.
  1 -> FAIL: hubo al menos una actualizacion perdida o un error.
  2 -> ERROR de entorno: la API no llego a estar lista (readiness).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_N = 100
DEFAULT_PER_OP_TIMEOUT_S = 5.0
DEFAULT_READINESS_TIMEOUT_S = 60
READINESS_POLL_S = 2
COBERTURA_PARCIAL_MSG = "COBERTURA PARCIAL: no mide el panel (depende de #3)"


class ErrorDeEntorno(RuntimeError):
    pass


@dataclass
class MuestraOperacion:
    indice: int
    marcador: str
    resultado: str  # "visto" | "perdida" | "error"
    latencia_s: float
    http_status_post: int | None
    http_status_get: int | None
    nota: str


def _http(method: str, url: str, body: dict | None = None, timeout: float = 10.0):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        parsed = json.loads(raw) if raw else None
        return resp.status, parsed


def esperar_readiness(base_url: str, timeout_s: int) -> None:
    limite = time.monotonic() + timeout_s
    ultimo_error = None
    while time.monotonic() < limite:
        try:
            status, body = _http("GET", base_url + "/health/social-split", timeout=5.0)
            if status == 200 and isinstance(body, dict) and body.get("status") == "UP":
                return
            ultimo_error = f"status HTTP {status}, body={body}"
        except (urllib.error.URLError, TimeoutError) as exc:
            ultimo_error = str(exc)
        time.sleep(READINESS_POLL_S)
    raise ErrorDeEntorno(f"Timeout de {timeout_s}s esperando readiness. Ultimo error: {ultimo_error}")


def ejecutar_operacion(base_url: str, indice: int, timeout_s: float) -> MuestraOperacion:
    marcador = f"LAT-{indice}-{uuid.uuid4().hex[:8]}"
    t0 = time.monotonic()
    try:
        status_post, body_post = _http(
            "POST",
            f"{base_url}/api/splits",
            {"hostMemberId": marcador, "totalAmount": "10.00", "currency": "USD"},
            timeout=timeout_s,
        )
    except (urllib.error.URLError, TimeoutError) as exc:
        # Nunca hubo respuesta al enviar: la actualizacion se considera perdida.
        return MuestraOperacion(indice, marcador, "perdida", timeout_s, None, None, f"sin respuesta al crear: {exc}")

    if status_post != 201 or not isinstance(body_post, dict) or "id" not in body_post:
        t1 = time.monotonic()
        return MuestraOperacion(
            indice, marcador, "error", t1 - t0, status_post, None, f"creacion devolvio status/cuerpo inesperado"
        )

    split_id = body_post["id"]

    try:
        status_get, body_get = _http("GET", f"{base_url}/api/splits/{split_id}", timeout=timeout_s)
    except (urllib.error.URLError, TimeoutError) as exc:
        return MuestraOperacion(
            indice, marcador, "perdida", timeout_s, status_post, None, f"sin respuesta al confirmar visibilidad: {exc}"
        )

    t1 = time.monotonic()
    if status_get == 200 and isinstance(body_get, dict) and body_get.get("hostMemberId") == marcador:
        return MuestraOperacion(indice, marcador, "visto", t1 - t0, status_post, status_get, "ok")

    return MuestraOperacion(
        indice,
        marcador,
        "perdida",
        timeout_s,
        status_post,
        status_get,
        f"la sesion no fue visible/consistente tras la escritura (status_get={status_get})",
    )


def percentil(valores_ordenados: list[float], p: float) -> float | None:
    """Percentil por interpolacion lineal (metodo estandar tipo numpy 'linear')."""
    n = len(valores_ordenados)
    if n == 0:
        return None
    if n == 1:
        return valores_ordenados[0]
    rango = (p / 100.0) * (n - 1)
    lo = int(rango)
    hi = min(lo + 1, n - 1)
    frac = rango - lo
    return valores_ordenados[lo] + (valores_ordenados[hi] - valores_ordenados[lo]) * frac


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--n", type=int, default=DEFAULT_N, help="numero de operaciones identificables (>=100)")
    parser.add_argument("--per-op-timeout", type=float, default=DEFAULT_PER_OP_TIMEOUT_S)
    parser.add_argument("--readiness-timeout", type=int, default=DEFAULT_READINESS_TIMEOUT_S)
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent / "latency-samples.json"),
        help="ruta del JSON con las muestras crudas",
    )
    args = parser.parse_args()

    if args.n < 100:
        print(f"ERROR DE ENTORNO: --n debe ser >= 100 (recibido {args.n})", file=sys.stderr)
        return 2

    print(f"[readiness] esperando /health/social-split en {args.base_url} ...")
    try:
        esperar_readiness(args.base_url, args.readiness_timeout)
    except ErrorDeEntorno as exc:
        print(f"ERROR DE ENTORNO: {exc}", file=sys.stderr)
        return 2
    print("[readiness] OK")

    muestras: list[MuestraOperacion] = []
    for i in range(args.n):
        muestras.append(ejecutar_operacion(args.base_url, i, args.per_op_timeout))

    enviados = len(muestras)
    vistos = sum(1 for m in muestras if m.resultado == "visto")
    perdidos = sum(1 for m in muestras if m.resultado == "perdida")
    errores = sum(1 for m in muestras if m.resultado == "error")

    # Regla dura: TODAS las latencias entran al percentil, incluidas perdidas/errores.
    latencias = sorted(m.latencia_s for m in muestras)
    p50 = percentil(latencias, 50)
    p95 = percentil(latencias, 95)
    maximo = max(latencias) if latencias else None

    salida = {
        "baseUrl": args.base_url,
        "n": args.n,
        "perOpTimeoutS": args.per_op_timeout,
        "enviados": enviados,
        "vistos": vistos,
        "perdidos": perdidos,
        "errores": errores,
        "p50S": p50,
        "p95S": p95,
        "maximoS": maximo,
        "coberturaParcial": COBERTURA_PARCIAL_MSG,
        "muestras": [asdict(m) for m in muestras],
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"enviados={enviados} vistos={vistos} perdidos={perdidos} errores={errores}")
    print(f"p50={p50:.4f}s p95={p95:.4f}s max={maximo:.4f}s" if latencias else "sin muestras de latencia")
    print(f"muestras crudas guardadas en: {out_path}")
    print(COBERTURA_PARCIAL_MSG)

    if perdidos > 0 or errores > 0:
        print(
            f"RESULTADO: FAIL ({perdidos} perdida(s) + {errores} error(es); "
            "las perdidas se incluyeron en el percentil, no se excluyeron)"
        )
        return 1

    print("RESULTADO: PASS (todas las operaciones fueron vistas, sin errores)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
