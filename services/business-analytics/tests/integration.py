"""Real broker, API, timer and restart checks for the isolated component Compose."""

import argparse
import json
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPIC = "bankpulse.social-split.events.v1"


def iso(value):
    return (
        datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")
    )


def event(session, version, kind, at, **payload):
    return {
        "eventId": f"{session}-{version}",
        "eventType": kind,
        "schemaVersion": 1,
        "aggregateId": session,
        "aggregateVersion": version,
        "occurredAt": iso(at),
        "payload": {"sessionId": session, **payload},
    }


def created(session, at, total="100", currency="USD"):
    return event(
        session,
        1,
        "SplitCreated",
        at,
        createdAt=iso(at),
        totalAmount=total,
        currency=currency,
    )


def run(docker):
    evidence = {"scope": "isolated analytics component", "checks": []}
    command = [docker, "compose", "-f", str(ROOT / "compose.test.yaml")]

    def compose(*args, data=None):
        return subprocess.run(
            command + list(args),
            input=data,
            text=True,
            capture_output=True,
            check=True,
            timeout=90,
        )

    def snapshot():
        with urllib.request.urlopen(
            "http://127.0.0.1:18080/snapshot", timeout=3
        ) as response:
            return json.load(response)

    def until(predicate, timeout=20):
        deadline, last = time.monotonic() + timeout, None
        while time.monotonic() < deadline:
            try:
                last = snapshot()
                if predicate(last):
                    return last
            except OSError:
                pass
            time.sleep(0.1)
        raise AssertionError(f"condition timed out: {last}")

    def send(events):
        code = (
            "import sys,json; from kafka import KafkaProducer; "
            "p=KafkaProducer(bootstrap_servers='broker:9092',acks='all',value_serializer=lambda v:json.dumps(v).encode()); "
            f"events=json.load(sys.stdin); [p.send('{TOPIC}',key=e['aggregateId'].encode(),value=e).get(timeout=10) for e in events]; p.close()"
        )
        compose(
            "exec", "-T", "analytics", "python", "-c", code, data=json.dumps(events)
        )

    def record(name, observed):
        evidence["checks"].append({"name": name, "observed": observed})
        print(json.dumps({"passed": name, "observed": observed}), flush=True)

    initial = until(lambda value: value.get("valid"))
    if initial["kpis"]["counts"]["sessions"]:
        raise AssertionError("integration requires a new dedicated component volume")
    record("empty population is SIN MUESTRA", initial["kpis"]["B-K1"])

    now = time.time()
    healthy = [
        created("healthy", now),
        event(
            "healthy",
            2,
            "ParticipantAdded",
            now + 0.1,
            participantId="p1",
            memberId="m1",
            shareAmount="60",
        ),
        event(
            "healthy",
            3,
            "ParticipantAuthorized",
            now + 0.2,
            participantId="p1",
            paymentReference="pay-1",
        ),
        event(
            "healthy",
            4,
            "ParticipantAdded",
            now + 0.3,
            participantId="p2",
            memberId="m2",
            shareAmount="40",
        ),
        event(
            "healthy",
            5,
            "ParticipantAuthorized",
            now + 0.4,
            participantId="p2",
            paymentReference="pay-2",
        ),
        event("healthy", 6, "SplitCompleted", now + 0.5, closedAt=iso(now + 0.5)),
    ]
    send(healthy)
    good = until(
        lambda value: value.get("valid")
        and value["kpis"]["counts"]["closedWindow"] == 1
    )
    assert good["kpis"]["B-K1"]["value"] == 100
    assert good["kpis"]["B-K2"]["value"] == {"USD": "0"}
    record("healthy 60+40 close", good["kpis"])

    send(healthy)
    duplicate = until(lambda value: value["diagnostics"]["duplicates"] == len(healthy))
    assert duplicate["kpis"]["counts"]["sessions"] == 1
    record("duplicate delivery has no double count", duplicate["diagnostics"])

    deadline_start = time.time() - 119.2
    waiting = [
        created("deadline", deadline_start),
        event(
            "deadline",
            2,
            "ParticipantAdded",
            deadline_start + 0.1,
            participantId="p1",
            memberId="m1",
            shareAmount="60",
        ),
        event(
            "deadline",
            3,
            "ParticipantAuthorized",
            deadline_start + 0.2,
            participantId="p1",
            paymentReference="pay-3",
        ),
    ]
    send(waiting)
    before = until(lambda value: value["kpis"]["counts"]["sessions"] == 2)
    assert before["kpis"]["B-K3"]["value"] == {}
    overdue = until(
        lambda value: value["kpis"]["B-K3"]["value"] == {"USD": "60"}, timeout=4
    )
    observed = datetime.fromisoformat(
        overdue["generatedAt"].replace("Z", "+00:00")
    ).timestamp()
    delay = observed - deadline_start - 120
    assert 0 < delay <= 1
    record(
        "deadline changes KPI without traffic",
        {"delaySeconds": delay, "kpi": overdue["kpis"]["B-K3"]},
    )

    revision = overdue["revision"]
    compose("restart", "analytics")
    restarted = until(
        lambda value: value.get("valid") and value["revision"] > revision, timeout=30
    )
    assert restarted["kpis"]["B-K3"]["value"] == {"USD": "60"}
    record(
        "restart restores state and timers",
        {"beforeRevision": revision, "afterRevision": restarted["revision"]},
    )

    late = time.time()
    send(
        [
            event(
                "reordered",
                2,
                "ParticipantAdded",
                late + 0.1,
                participantId="p1",
                memberId="m1",
                shareAmount="100",
            )
        ]
    )
    incomplete = until(lambda value: value["quality"] == "INCOMPLETO")
    assert incomplete["coverage"]["pendingEvents"] == 1
    send([created("reordered", late)])
    repaired = until(
        lambda value: value.get("valid") and value["kpis"]["counts"]["sessions"] == 3
    )
    record("out-of-order history repairs", repaired["coverage"])
    evidence["finishedAt"] = iso(time.time())
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.docker)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
