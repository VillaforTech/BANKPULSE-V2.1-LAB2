"""Pruebas de los KPIs de negocio B-K1/B-K2/B-K3 (issue #5).

El reloj SIEMPRE se inyecta como el parametro `ahora`; estas pruebas jamas
llaman a `datetime.now()`/`time.time()` reales, para que sean deterministas
y no dependan de cuando se ejecuten.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from tests.kpis.bank_kpis import calcular_b_k1, calcular_b_k2, calcular_b_k3

AHORA = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _sesion(
    total,
    currency="USD",
    status="OPEN",
    creada_hace_s=0,
    cerrada_hace_s=None,
    participantes=None,
):
    """Fabrica una sesion de prueba con Decimal para todos los montos."""
    return {
        "id": "s-test",
        "totalAmount": Decimal(str(total)),
        "currency": currency,
        "status": status,
        "createdAt": AHORA - timedelta(seconds=creada_hace_s),
        "closedAt": None if cerrada_hace_s is None else AHORA - timedelta(seconds=cerrada_hace_s),
        "participants": participantes or [],
    }


def _participante(share, authorized=True, ref="PAY-REF-1"):
    return {
        "shareAmount": Decimal(str(share)),
        "authorized": authorized,
        "paymentReference": ref,
    }


# ---------------------------------------------------------------------------
# Caso del criterio de aceptacion: el falso verde de extremo a extremo.
# total=100, cerrada con cuotas autorizadas 60+30 (descuadre de 10).
# ---------------------------------------------------------------------------


def test_falso_verde_60_30_de_100_reporta_b_k1_cero_en_cohorte_aislada():
    sesion_descuadrada = _sesion(
        total=100,
        status="COMPLETED",
        cerrada_hace_s=60,
        participantes=[_participante(60), _participante(30)],
    )

    b_k1 = calcular_b_k1([sesion_descuadrada], AHORA)

    assert b_k1 == 0.0
    assert b_k1 < 100


def test_falso_verde_60_30_de_100_reporta_b_k2_diez_dolares_de_descuadre():
    sesion_descuadrada = _sesion(
        total=100,
        status="COMPLETED",
        cerrada_hace_s=60,
        participantes=[_participante(60), _participante(30)],
    )

    b_k2 = calcular_b_k2([sesion_descuadrada], AHORA)

    assert b_k2 == {"USD": Decimal("10")}


# ---------------------------------------------------------------------------
# Cierre sano: 60+40 de 100 -> sin descuadre, 100% valido.
# ---------------------------------------------------------------------------


def test_cierre_sano_60_40_de_100_reporta_b_k1_cien():
    sesion_sana = _sesion(
        total=100,
        status="COMPLETED",
        cerrada_hace_s=60,
        participantes=[_participante(60), _participante(40)],
    )

    assert calcular_b_k1([sesion_sana], AHORA) == 100.0


def test_cierre_sano_60_40_de_100_reporta_b_k2_cero():
    sesion_sana = _sesion(
        total=100,
        status="COMPLETED",
        cerrada_hace_s=60,
        participantes=[_participante(60), _participante(40)],
    )

    assert calcular_b_k2([sesion_sana], AHORA) == {"USD": Decimal("0")}


# ---------------------------------------------------------------------------
# Casos invalidos adicionales para B-K1.
# ---------------------------------------------------------------------------


def test_cierre_sin_participantes_es_invalido():
    sesion_vacia = _sesion(total=100, status="COMPLETED", cerrada_hace_s=30, participantes=[])

    assert calcular_b_k1([sesion_vacia], AHORA) == 0.0


def test_participante_sin_autorizar_hace_invalido_el_cierre():
    sesion = _sesion(
        total=100,
        status="COMPLETED",
        cerrada_hace_s=30,
        participantes=[_participante(60), _participante(40, authorized=False)],
    )

    assert calcular_b_k1([sesion], AHORA) == 0.0


def test_referencia_de_pago_vacia_hace_invalido_el_cierre():
    sesion = _sesion(
        total=100,
        status="COMPLETED",
        cerrada_hace_s=30,
        participantes=[_participante(60), _participante(40, ref="")],
    )

    assert calcular_b_k1([sesion], AHORA) == 0.0


def test_referencia_de_pago_none_hace_invalido_el_cierre():
    sesion = _sesion(
        total=100,
        status="COMPLETED",
        cerrada_hace_s=30,
        participantes=[_participante(60), _participante(40, ref=None)],
    )

    assert calcular_b_k1([sesion], AHORA) == 0.0


def test_cuota_no_positiva_hace_invalido_el_cierre():
    sesion = _sesion(
        total=100,
        status="COMPLETED",
        cerrada_hace_s=30,
        participantes=[_participante(100), _participante(0)],
    )

    assert calcular_b_k1([sesion], AHORA) == 0.0


# ---------------------------------------------------------------------------
# Monedas separadas: nunca se suman entre si.
# ---------------------------------------------------------------------------


def test_dos_monedas_distintas_no_se_suman_entre_si_en_b_k2():
    sesion_usd = _sesion(
        total=100,
        currency="USD",
        status="COMPLETED",
        cerrada_hace_s=30,
        participantes=[_participante(60), _participante(30)],  # descuadre 10 USD
    )
    sesion_eur = _sesion(
        total=50,
        currency="EUR",
        status="COMPLETED",
        cerrada_hace_s=30,
        participantes=[_participante(20), _participante(20)],  # descuadre 10 EUR
    )

    b_k2 = calcular_b_k2([sesion_usd, sesion_eur], AHORA)

    assert b_k2 == {"USD": Decimal("10"), "EUR": Decimal("10")}
    # cada moneda es su propia clave: nunca se combinan en un solo numero
    assert set(b_k2.keys()) == {"USD", "EUR"}


def test_dos_monedas_distintas_no_se_suman_entre_si_en_b_k3():
    sesion_usd = _sesion(
        total=100,
        currency="USD",
        status="OPEN",
        creada_hace_s=121,
        participantes=[_participante(60)],
    )
    sesion_eur = _sesion(
        total=100,
        currency="EUR",
        status="OPEN",
        creada_hace_s=121,
        participantes=[_participante(25)],
    )

    b_k3 = calcular_b_k3([sesion_usd, sesion_eur], AHORA)

    assert b_k3 == {"USD": Decimal("60"), "EUR": Decimal("25")}


# ---------------------------------------------------------------------------
# B-K3: exposicion de sesiones abiertas "viejas".
# ---------------------------------------------------------------------------


def test_b_k3_sesion_open_con_60_autorizados_y_edad_121s_cuenta():
    sesion_vieja_abierta = _sesion(
        total=100,
        status="OPEN",
        creada_hace_s=121,
        participantes=[_participante(60)],
    )

    b_k3 = calcular_b_k3([sesion_vieja_abierta], AHORA, edad_min_s=120)

    assert b_k3 == {"USD": Decimal("60")}


def test_b_k3_sesion_open_por_debajo_del_umbral_de_edad_no_cuenta():
    sesion_reciente_abierta = _sesion(
        total=100,
        status="OPEN",
        creada_hace_s=119,
        participantes=[_participante(60)],
    )

    b_k3 = calcular_b_k3([sesion_reciente_abierta], AHORA, edad_min_s=120)

    assert b_k3 == {}


def test_b_k3_ignora_sesiones_ya_cerradas_sin_importar_la_edad():
    sesion_cerrada_vieja = _sesion(
        total=100,
        status="COMPLETED",
        creada_hace_s=10_000,
        cerrada_hace_s=9_000,
        participantes=[_participante(60), _participante(40)],
    )

    b_k3 = calcular_b_k3([sesion_cerrada_vieja], AHORA, edad_min_s=120)

    assert b_k3 == {}


# ---------------------------------------------------------------------------
# Cohorte vacia -> "SIN MUESTRA" (solo aplica a B-K1, que es un ratio).
# ---------------------------------------------------------------------------


def test_cohorte_vacia_reporta_sin_muestra_en_b_k1():
    assert calcular_b_k1([], AHORA) == "SIN MUESTRA"


def test_cohorte_vacia_por_ventana_vencida_reporta_sin_muestra_en_b_k1():
    sesion_cerrada_hace_mucho = _sesion(
        total=100,
        status="COMPLETED",
        cerrada_hace_s=901,  # fuera de la ventana de 900s (15 min)
        participantes=[_participante(60), _participante(40)],
    )

    assert calcular_b_k1([sesion_cerrada_hace_mucho], AHORA, ventana_s=900) == "SIN MUESTRA"


def test_cohorte_vacia_reporta_diccionarios_vacios_en_b_k2_y_b_k3():
    assert calcular_b_k2([], AHORA) == {}
    assert calcular_b_k3([], AHORA) == {}


# ---------------------------------------------------------------------------
# B-K1 con cohorte mixta: valida el promedio ponderado del porcentaje.
# ---------------------------------------------------------------------------


def test_b_k1_con_cohorte_mixta_calcula_porcentaje_correcto():
    sana = _sesion(
        total=100,
        status="COMPLETED",
        cerrada_hace_s=30,
        participantes=[_participante(60), _participante(40)],
    )
    descuadrada = _sesion(
        total=100,
        status="COMPLETED",
        cerrada_hace_s=30,
        participantes=[_participante(60), _participante(30)],
    )
    otra_sana = _sesion(
        total=50,
        status="COMPLETED",
        cerrada_hace_s=30,
        participantes=[_participante(50)],
    )

    b_k1 = calcular_b_k1([sana, descuadrada, otra_sana], AHORA)

    assert b_k1 == pytest.approx(200.0 / 3.0)
