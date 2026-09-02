#!/usr/bin/env bash
set -euo pipefail
base_url="${BANKPULSE_URL:-http://localhost:8080}"

echo "[V2 1/6] Health checks de seis microservicios"
for service in payments audit experiences travel events social-split; do
  curl -fsS "$base_url/health/$service" | grep -q '"status":"UP"'
done

echo "[V2 2/6] Experiences API"
curl -fsS "$base_url/api/experiences" | grep -q 'GASTRONOMY'

echo "[V2 3/6] Travel eligibility + signed credential"
curl -fsS "$base_url/api/travel/eligibility/MEMBER-001" | grep -q '"eligible":true'
curl -fsS -X POST "$base_url/api/travel/credentials" -H 'Content-Type: application/json' -d '{"memberId":"MEMBER-001","benefitCode":"LOUNGE-ANNUAL"}' | grep -q 'OFFLINE_VERIFIABLE_DEMO'

echo "[V2 4/6] Events API + Redis seat hold"
event_id="$(curl -fsS "$base_url/api/events" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p' | head -1)"
test -n "$event_id"
hold="$(curl -fsS -X POST "$base_url/api/events/$event_id/holds" -H 'Content-Type: application/json' -d '{"seatId":"A-12","memberId":"MEMBER-001"}')"
echo "$hold" | grep -q '"seatId":"A-12"'
curl -fsS "$base_url/api/events/$event_id/holds" | grep -q '"seatId":"A-12"'
http_code="$(curl -sS -o /tmp/second-hold.out -w '%{http_code}' -X POST "$base_url/api/events/$event_id/holds" -H 'Content-Type: application/json' -d '{"seatId":"A-12","memberId":"MEMBER-002"}')"
test "$http_code" = "409"

echo "[V2 5/6] Social Split lifecycle"
split="$(curl -fsS -X POST "$base_url/api/splits" -H 'Content-Type: application/json' -d '{"hostMemberId":"MEMBER-001","totalAmount":100.00,"currency":"USD"}')"
split_id="$(echo "$split" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')"
test -n "$split_id"
curl -fsS -X POST "$base_url/api/splits/$split_id/participants" -H 'Content-Type: application/json' -d '{"memberId":"MEMBER-002","shareAmount":50.00}' | grep -q 'MEMBER-002'

echo "[V2 6/6] Core payment/outbox regression"
bash scripts/smoke.sh

echo "BANKdragon V2.1 interactive smoke test OK"
