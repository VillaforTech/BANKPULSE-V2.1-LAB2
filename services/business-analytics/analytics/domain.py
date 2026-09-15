"""Pure Social Split projection and KPI calculations with a caller supplied clock."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

EVENT_TYPES = {
    "SplitCreated",
    "ParticipantAdded",
    "ParticipantAuthorized",
    "SplitCompleted",
}


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO-8601 string with timezone")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone is required")
    return result.timestamp()


def iso(value):
    return (
        datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")
    )


def amount(value, *, positive=False):
    if isinstance(value, bool):
        raise ValueError("boolean amount")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("invalid amount") from exc
    if not result.is_finite() or result < 0 or (positive and result <= 0):
        raise ValueError(
            "amount must be finite and positive"
            if positive
            else "amount must be finite and nonnegative"
        )
    return result


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    return value.strip()


def validate(event):
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    for key in ("eventId", "aggregateId"):
        _text(event.get(key), key)
    if type(event.get("schemaVersion")) is not int or event["schemaVersion"] != 1:
        raise ValueError("unsupported schemaVersion")
    if type(event.get("aggregateVersion")) is not int or event["aggregateVersion"] < 1:
        raise ValueError("aggregateVersion must be a positive integer")
    if event.get("eventType") not in EVENT_TYPES:
        raise ValueError("unknown eventType")
    timestamp(event.get("occurredAt"))
    payload = event.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if payload.get("sessionId") != event["aggregateId"]:
        raise ValueError("payload identity mismatch")
    kind = event["eventType"]
    if kind == "SplitCreated":
        if event["aggregateVersion"] != 1:
            raise ValueError("SplitCreated must be aggregate version 1")
        created = timestamp(payload.get("createdAt"))
        if timestamp(event["occurredAt"]) < created:
            raise ValueError("event precedes creation")
        amount(payload.get("totalAmount"), positive=True)
        currency = _text(payload.get("currency"), "currency")
        if len(currency) != 3 or currency != currency.upper():
            raise ValueError("currency must be an uppercase ISO-style code")
    elif kind == "ParticipantAdded":
        _text(payload.get("participantId"), "participantId")
        _text(payload.get("memberId"), "memberId")
        amount(payload.get("shareAmount"), positive=True)
    elif kind == "ParticipantAuthorized":
        _text(payload.get("participantId"), "participantId")
        _text(payload.get("paymentReference"), "paymentReference")
    elif kind == "SplitCompleted":
        closed = timestamp(payload.get("closedAt"))
        if closed != timestamp(event["occurredAt"]):
            raise ValueError("closedAt must match the persisted transition")
    return event


def project(previous, event, deadline_seconds=120):
    payload = event["payload"]
    kind = event["eventType"]
    occurred = timestamp(event["occurredAt"])
    if previous is None:
        if kind != "SplitCreated":
            raise ValueError("missing SplitCreated")
        created = timestamp(payload["createdAt"])
        return {
            "sessionId": event["aggregateId"],
            "version": 1,
            "status": "OPEN",
            "createdAt": created,
            "closedAt": None,
            "totalAmount": str(amount(payload["totalAmount"], positive=True)),
            "currency": payload["currency"],
            "participants": {},
            "deadline": created + deadline_seconds,
            "occurredAt": occurred,
        }
    if event["aggregateVersion"] != previous["version"] + 1:
        raise ValueError("aggregate version is not consecutive")
    if previous["status"] == "COMPLETED":
        raise ValueError("completed session cannot change")
    if occurred < previous["occurredAt"]:
        raise ValueError("transition time moved backwards")
    result = dict(previous, version=event["aggregateVersion"], occurredAt=occurred)
    result["participants"] = dict(previous["participants"])
    if kind == "ParticipantAdded":
        participant_id = payload["participantId"]
        if participant_id in result["participants"]:
            raise ValueError("participant already exists")
        result["participants"][participant_id] = {
            "memberId": payload["memberId"],
            "shareAmount": str(amount(payload["shareAmount"], positive=True)),
            "authorized": False,
            "paymentReference": None,
        }
    elif kind == "ParticipantAuthorized":
        participant_id = payload["participantId"]
        if participant_id not in result["participants"]:
            raise ValueError("unknown participant")
        participant = dict(result["participants"][participant_id])
        participant.update(
            authorized=True, paymentReference=payload["paymentReference"]
        )
        result["participants"][participant_id] = participant
    elif kind == "SplitCompleted":
        result.update(status="COMPLETED", closedAt=timestamp(payload["closedAt"]))
    else:
        raise ValueError("SplitCreated cannot repeat")
    return result


def valid_close(session):
    participants = list(session["participants"].values())
    valid_participants = bool(participants) and all(
        amount(p["shareAmount"], positive=True) > 0
        and p["authorized"]
        and isinstance(p["paymentReference"], str)
        and bool(p["paymentReference"].strip())
        for p in participants
    )
    shares = sum((amount(p["shareAmount"]) for p in participants), Decimal(0))
    return valid_participants and shares == amount(session["totalAmount"])


def _money(values):
    return {key: str(values[key]) for key in sorted(values)}


def calculate(sessions, now):
    closed = [
        s
        for s in sessions
        if s["status"] == "COMPLETED" and s["closedAt"] <= now < s["closedAt"] + 900
    ]
    valid = [s for s in closed if valid_close(s)]
    closure_gap = {}
    for session in closed:
        authorized = sum(
            (
                amount(p["shareAmount"])
                for p in session["participants"].values()
                if p["authorized"]
            ),
            Decimal(0),
        )
        currency = session["currency"]
        closure_gap[currency] = closure_gap.get(currency, Decimal(0)) + abs(
            amount(session["totalAmount"]) - authorized
        )
    stale = [s for s in sessions if s["status"] == "OPEN" and now > s["deadline"]]
    stale_amount = {}
    for session in stale:
        value = sum(
            (
                amount(p["shareAmount"])
                for p in session["participants"].values()
                if p["authorized"]
            ),
            Decimal(0),
        )
        currency = session["currency"]
        stale_amount[currency] = stale_amount.get(currency, Decimal(0)) + value
    k1 = None if not closed else 100 * len(valid) / len(closed)
    gap_values, stale_values = _money(closure_gap), _money(stale_amount)
    return {
        "B-K1": {
            "value": k1,
            "unit": "percent",
            "sample": len(closed),
            "state": "SIN MUESTRA"
            if not closed
            else "SANO"
            if len(valid) == len(closed)
            else "INCUMPLIDO",
        },
        "B-K2": {
            "value": gap_values,
            "unit": "demo_money_by_currency",
            "sample": len(closed),
            "state": "INCUMPLIDO"
            if any(Decimal(v) > 0 for v in gap_values.values())
            else "SANO",
        },
        "B-K3": {
            "value": stale_values,
            "unit": "demo_money_by_currency",
            "sample": len(stale),
            "state": "INCUMPLIDO"
            if any(Decimal(v) > 0 for v in stale_values.values())
            else "SANO",
        },
        "counts": {
            "sessions": len(sessions),
            "closedWindow": len(closed),
            "validClosedWindow": len(valid),
            "staleOpen": len(stale),
        },
    }
