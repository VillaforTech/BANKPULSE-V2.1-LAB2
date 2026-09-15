#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${SOCIAL_SPLIT_URL:-http://localhost:8086}"
command -v curl >/dev/null
curl -fsS "$BASE_URL/actuator/health" >/dev/null

create_session() { curl -fsS -X POST "$BASE_URL/api/splits" -H 'Content-Type: application/json' -d '{"hostMemberId":"BUSINESS-TEST","totalAmount":100,"currency":"USD"}'; }
json_id() { sed -n 's/.*"id":"\([^"]*\)".*/\1/p'; }
expect_rejection() { test "$(curl -s -o /dev/null -w '%{http_code}' "$@")" -ge 400; }

session="$(create_session)"; id="$(printf '%s' "$session" | json_id)"
test -n "$id"
for share in 60 40; do curl -fsS -X POST "$BASE_URL/api/splits/$id/participants" -H 'Content-Type: application/json' -d "{\"memberId\":\"M-$share\",\"shareAmount\":$share}" >/tmp/social-split-$share.json; done
for participant in $(sed -n 's/.*"id":"\([^"]*\)".*/\1/p' /tmp/social-split-60.json /tmp/social-split-40.json); do curl -fsS -X POST "$BASE_URL/api/splits/$id/participants/$participant/authorize" -H 'Content-Type: application/json' -d '{"paymentReference":"demo-reference"}' >/dev/null; done
curl -fsS -X POST "$BASE_URL/api/splits/$id/close" >/tmp/social-split-closed.json
grep -q '"status":"COMPLETED"' /tmp/social-split-closed.json
curl -fsS -X POST "$BASE_URL/api/splits/$id/close" >/dev/null

empty="$(create_session)"; empty_id="$(printf '%s' "$empty" | json_id)"
expect_rejection -X POST "$BASE_URL/api/splits/$empty_id/close"
unauthorized="$(create_session)"; unauthorized_id="$(printf '%s' "$unauthorized" | json_id)"
curl -fsS -X POST "$BASE_URL/api/splits/$unauthorized_id/participants" -H 'Content-Type: application/json' -d '{"memberId":"NO-CONSENT","shareAmount":100}' >/dev/null
expect_rejection -X POST "$BASE_URL/api/splits/$unauthorized_id/close"

for shares in '60,30' '60,50'; do bad="$(create_session)"; bid="$(printf '%s' "$bad" | json_id)"; for share in ${shares//,/ }; do curl -fsS -X POST "$BASE_URL/api/splits/$bid/participants" -H 'Content-Type: application/json' -d "{\"memberId\":\"BAD-$share\",\"shareAmount\":$share}" >/dev/null; done; expect_rejection -X POST "$BASE_URL/api/splits/$bid/close"; done
echo 'business-test: healthy close, invalid totals, and repeated close passed'