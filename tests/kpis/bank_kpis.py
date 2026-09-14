"""Calculadoras puras de los KPIs de negocio del deber-01 (issue #5).

Este modulo NO hace red ni accede a base de datos: recibe estructuras de
Python ya materializadas (listas de "sesiones" de Social Split) y un reloj
inyectado (`ahora`), y devuelve el KPI calculado. Todo el dinero se maneja
con `decimal.Decimal`; NUNCA se usa `float` para montos, para evitar errores
de redondeo binario en calculos financieros.

Forma esperada de una "sesion" (dict):
    {
        "id": str,
        "totalAmount": Decimal,
        "currency": str,               # p.ej. "USD"
        "status": str,                 # "OPEN" | "COMPLETED" (u otro)
        "createdAt": datetime,         # tz-aware
        "closedAt": datetime | None,   # tz-aware; None si sigue OPEN
        "participants": [
            {
                "shareAmount": Decimal,
                "authorized": bool,
                "paymentReference": str | None,
            },
            ...
        ],
    }

NOTA IMPORTANTE (alcance): el modelo real de `SplitSession` (ver
services/social-split-api) NO persiste hoy un timestamp de cierre
(`closedAt`); ese campo es una hipotesis de trabajo para este calculador de
KPIs (lo aportaria el evento/outbox de cierre que crea el issue #1/#4). Estas
funciones son deliberadamente puras y agnosticas de esa fuente: aceptan el
campo como entrada y no adivinan de donde salio.

ADVERTENCIA DE ALCANCE PARA B-K2 y B-K3: ambos KPIs expresan EXPOSICION o
COMPROMISOS de una demo academica (montos descuadrados o comprometidos en
sesiones abiertas). NO representan cobros reales ni perdidas financieras
demostradas; BankPulse es un laboratorio y ninguna de estas sesiones mueve
dinero real.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Union

Sesion = dict[str, Any]

_CERO = Decimal("0")


def _en_ventana(closed_at: datetime | None, ahora: datetime, ventana_s: int) -> bool:
    """True si `closed_at` cayo dentro de los ultimos `ventana_s` segundos, visto desde `ahora`."""
    if closed_at is None:
        return False
    delta_s = (ahora - closed_at).total_seconds()
    return 0 <= delta_s <= ventana_s


def _cohorte_cerradas_en_ventana(sesiones: list[Sesion], ahora: datetime, ventana_s: int) -> list[Sesion]:
    return [s for s in sesiones if _en_ventana(s.get("closedAt"), ahora, ventana_s)]


def _suma_cuotas_autorizadas(sesion: Sesion) -> Decimal:
    return sum(
        (p["shareAmount"] for p in sesion.get("participants", []) if p.get("authorized")),
        start=_CERO,
    )


def _es_cierre_valido(sesion: Sesion) -> bool:
    """Un cierre valido exige: participantes no vacios, cuotas positivas que
    suman EXACTAMENTE totalAmount, todos autorizados y referencias de pago
    no vacias. Esta es la regla de negocio real (issue #1 debe hacer que el
    backend la respete); hoy `closeIfAuthorized()` NO la valida, por eso este
    calculador existe: para poder DETECTAR el falso verde comparando contra
    lo que la API realmente dejo pasar."""
    participantes = sesion.get("participants", [])
    if not participantes:
        return False
    if any(p["shareAmount"] <= _CERO for p in participantes):
        return False
    if not all(p.get("authorized") for p in participantes):
        return False
    if any(not (p.get("paymentReference") or "").strip() for p in participantes):
        return False
    suma_cuotas = sum((p["shareAmount"] for p in participantes), start=_CERO)
    return suma_cuotas == sesion["totalAmount"]


def calcular_b_k1(
    sesiones: list[Sesion], ahora: datetime, ventana_s: int = 900
) -> Union[float, str]:
    """B-K1 = 100 * (cierres validos) / (sesiones cerradas en los ultimos `ventana_s` s).

    Devuelve el literal "SIN MUESTRA" (str) si no hubo ninguna sesion cerrada
    en la ventana, para no reportar un porcentaje ficticio sobre cero
    muestras. En caso contrario devuelve un float (es un ratio, no dinero).
    """
    cohorte = _cohorte_cerradas_en_ventana(sesiones, ahora, ventana_s)
    if not cohorte:
        return "SIN MUESTRA"
    validos = sum(1 for s in cohorte if _es_cierre_valido(s))
    return 100.0 * validos / len(cohorte)


def calcular_b_k2(
    sesiones: list[Sesion], ahora: datetime, ventana_s: int = 900
) -> dict[str, Decimal]:
    """B-K2 = suma de abs(totalAmount - suma_cuotas_autorizadas) de las
    sesiones cerradas en los ultimos `ventana_s` s, con cada moneda
    mantenida por separado (nunca se convierten ni se suman entre si).

    Ver advertencia de alcance en el docstring del modulo: este numero es
    exposicion/descuadre de una demo, no una perdida financiera real.
    """
    cohorte = _cohorte_cerradas_en_ventana(sesiones, ahora, ventana_s)
    resultado: dict[str, Decimal] = {}
    for s in cohorte:
        descuadre = abs(s["totalAmount"] - _suma_cuotas_autorizadas(s))
        moneda = s["currency"]
        resultado[moneda] = resultado.get(moneda, _CERO) + descuadre
    return resultado


def calcular_b_k3(
    sesiones: list[Sesion], ahora: datetime, edad_min_s: int = 120
) -> dict[str, Decimal]:
    """B-K3 = suma de cuotas autorizadas de sesiones todavia OPEN cuya edad
    (ahora - createdAt) supera `edad_min_s` segundos, por moneda. Es una foto
    del instante `ahora`: NO se limita a los ultimos 15 minutos.

    Ver advertencia de alcance en el docstring del modulo: este numero es
    exposicion/compromiso de una demo, no dinero realmente en riesgo.
    """
    resultado: dict[str, Decimal] = {}
    for s in sesiones:
        if s.get("status") != "OPEN":
            continue
        creada = s["createdAt"]
        edad_s = (ahora - creada).total_seconds()
        if edad_s > edad_min_s:
            moneda = s["currency"]
            resultado[moneda] = resultado.get(moneda, _CERO) + _suma_cuotas_autorizadas(s)
    return resultado
