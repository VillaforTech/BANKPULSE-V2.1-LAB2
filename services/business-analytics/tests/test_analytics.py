import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from analytics.app import create_app, fresh_view, metrics
from analytics.domain import calculate, project, validate
from analytics.store import Store


BASE = 2_000_000_000.0


def event(kind, version, payload=None, session="split-1", at=BASE):
    base = {"sessionId": session}
    if kind == "SplitCreated":
        base.update(createdAt="2033-05-18T03:33:20Z", totalAmount="100", currency="USD")
    base.update(payload or {})
    return {
        "eventId": f"{session}-{version}",
        "eventType": kind,
        "schemaVersion": 1,
        "aggregateId": session,
        "aggregateVersion": version,
        "occurredAt": __import__("analytics.domain", fromlist=["iso"]).iso(at),
        "payload": base,
    }


def history(
    shares=("60", "40"),
    authorize=True,
    complete=True,
    session="split-1",
    close_at=BASE + 5,
):
    events = [event("SplitCreated", 1, session=session)]
    version = 2
    for index, share in enumerate(shares, 1):
        participant = f"p{index}"
        events.append(
            event(
                "ParticipantAdded",
                version,
                {
                    "participantId": participant,
                    "memberId": f"m{index}",
                    "shareAmount": share,
                },
                session,
                BASE + version - 1,
            )
        )
        version += 1
        if authorize:
            events.append(
                event(
                    "ParticipantAuthorized",
                    version,
                    {"participantId": participant, "paymentReference": f"pay-{index}"},
                    session,
                    BASE + version - 1,
                )
            )
            version += 1
    if complete:
        events.append(
            event(
                "SplitCompleted",
                version,
                {
                    "closedAt": __import__("analytics.domain", fromlist=["iso"]).iso(
                        close_at
                    )
                },
                session,
                close_at,
            )
        )
    return events


def projected(events):
    current = None
    for item in events:
        validate(item)
        current = project(current, item)
    return current


def live(store, now):
    return store.publish(now, connected=True, caught_up=True, last_poll=now, lag=0)


def test_valid_close_is_healthy():
    result = calculate([projected(history())], BASE + 10)
    assert result["B-K1"] == {
        "value": 100.0,
        "unit": "percent",
        "sample": 1,
        "state": "SANO",
    }
    assert result["B-K2"]["value"] == {"USD": "0"}


@pytest.mark.parametrize("shares,gap", [(("60", "30"), "10"), (("60", "50"), "10")])
def test_well_formed_invalid_close_counts_violation(shares, gap):
    result = calculate([projected(history(shares=shares))], BASE + 10)
    assert result["B-K1"]["value"] == 0
    assert result["B-K1"]["state"] == "INCUMPLIDO"
    assert result["B-K2"]["value"] == {"USD": gap}


def test_no_close_is_no_sample():
    result = calculate([projected(history(complete=False))], BASE + 10)
    assert result["B-K1"]["value"] is None
    assert result["B-K1"]["state"] == "SIN MUESTRA"


def test_close_expires_at_exactly_fifteen_minutes():
    session = projected(history(close_at=BASE + 5))
    assert calculate([session], BASE + 904.999)["B-K1"]["sample"] == 1
    assert calculate([session], BASE + 905)["B-K1"]["sample"] == 0


def test_open_authorized_amount_appears_strictly_after_120_seconds():
    session = projected(history(shares=("60",), complete=False))
    assert calculate([session], BASE + 120)["B-K3"]["value"] == {}
    assert calculate([session], BASE + 120.001)["B-K3"]["value"] == {"USD": "60"}


def test_money_stays_separated_by_currency():
    usd = projected(history(shares=("60", "30"), session="usd"))
    eur_events = history(shares=("50", "40"), session="eur")
    eur_events[0]["payload"]["currency"] = "EUR"
    eur = projected(eur_events)
    assert calculate([usd, eur], BASE + 10)["B-K2"]["value"] == {
        "EUR": "10",
        "USD": "10",
    }


def test_schema_failure_is_rejected():
    bad = event("SplitCreated", 1)
    bad["schemaVersion"] = 2
    with pytest.raises(ValueError, match="schemaVersion"):
        validate(bad)


def test_blank_payment_reference_is_rejected():
    bad = event(
        "ParticipantAuthorized", 2, {"participantId": "p1", "paymentReference": " "}
    )
    with pytest.raises(ValueError, match="paymentReference"):
        validate(bad)


def test_completed_session_cannot_change():
    session = projected(history())
    next_event = event(
        "ParticipantAdded",
        session["version"] + 1,
        {"participantId": "p3", "memberId": "m3", "shareAmount": "1"},
        at=BASE + 9,
    )
    with pytest.raises(ValueError, match="cannot change"):
        project(session, next_event)


def test_store_deduplicates_and_restores(tmp_path):
    path = tmp_path / "analytics.sqlite"
    store = Store(path, "2033-05-18T03:33:20Z")
    for item in history():
        store.ingest(item)
    store.ingest(history()[0])
    first = live(store, BASE + 10)
    store.close()
    restored = Store(path, "2033-05-18T03:33:20Z")
    second = live(restored, BASE + 10)
    assert first["kpis"] == second["kpis"]
    assert second["diagnostics"]["duplicates"] == 1
    restored.close()


def test_out_of_order_event_is_pending_then_repaired(tmp_path):
    store = Store(tmp_path / "db", "2033-05-18T03:33:20Z")
    events = history(shares=("100",), complete=False)
    store.ingest(events[1])
    assert live(store, BASE + 10)["quality"] == "INCOMPLETO"
    store.ingest(events[0])
    assert live(store, BASE + 10)["quality"] == "ACTUAL"
    store.close()


def test_conflicting_event_identity_is_visible(tmp_path):
    store = Store(tmp_path / "db", "2033-05-18T03:33:20Z")
    original = event("SplitCreated", 1)
    store.ingest(original)
    changed = dict(original, payload=dict(original["payload"], totalAmount="101"))
    store.ingest(changed)
    assert live(store, BASE + 10)["coverage"]["schemaErrors"] == 1
    store.close()


def test_checkpoint_advances_after_durable_ingest(tmp_path):
    store = Store(tmp_path / "db", "2033-05-18T03:33:20Z")
    store.ingest(event("SplitCreated", 1), partition=2, offset=8)
    assert store.checkpoint(2) == 9
    store.close()


def test_api_snapshot_updates_and_metrics(tmp_path):
    store = Store(tmp_path / "db", "2033-05-18T03:33:20Z")
    for item in history():
        store.ingest(item)
    live(store, BASE + 10)
    app = create_app(store, run_consumer=False)
    with TestClient(app) as client:
        assert client.get("/snapshot").status_code == 200
        assert client.get("/updates?after=0").json()["snapshots"]
        assert "bankpulse_split_closed_window" in client.get("/metrics").text
    store.close()


def test_stale_snapshot_does_not_claim_validity(tmp_path):
    store = Store(tmp_path / "db", "2033-05-18T03:33:20Z")
    live(store, BASE)
    result = fresh_view(store, BASE + 4)
    assert result["quality"] == "DESACTUALIZADO"
    assert result["valid"] is False
    assert all(alert["active"] is None for alert in result["alerts"].values())
    store.close()


def test_invalid_projection_exports_nan_business_metrics(tmp_path):
    store = Store(tmp_path / "db")
    snapshot = store.publish(BASE)
    assert b"bankpulse_split_closed_window NaN" in metrics(snapshot)
    store.close()


def test_fixture_is_reproducible(tmp_path):
    fixture = Path(__file__).parent / "fixtures" / "social_split.ndjson"
    store = Store(tmp_path / "db", "2033-05-18T03:33:20Z")
    for line in fixture.read_text().splitlines():
        store.ingest(json.loads(line))
    result = live(store, BASE + 130)
    assert result["kpis"]["B-K1"]["value"] == 100
    assert result["kpis"]["B-K3"]["value"] == {"USD": "60"}
    store.close()
