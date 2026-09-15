#!/usr/bin/env python3
"""Verify the exact smoke fixture in SQL and its correlated audit event."""
import json, re, subprocess, sys, urllib.request
from pathlib import Path
base, output = sys.argv[1:]
p = json.loads(Path(output, 'bankpulse-payment.json').read_text())
assert p == json.loads(Path(output, 'bankpulse-payment-retry.json').read_text())
assert p['account'] == 'EC-4242' and p['amount'] == 27.5 and p['currency'] == 'USD' and p['status'] == 'ACCEPTED'
assert re.fullmatch(r'[a-zA-Z0-9-]+', p['idempotencyKey'])
assert re.fullmatch(r'[a-f0-9-]+', p['id'])
sql = "SELECT count(*) FROM payments WHERE idempotency_key='%s'; SELECT count(*) FROM outbox_events WHERE aggregate_id='%s' AND event_type='PAYMENT_CREATED';" % (p['idempotencyKey'], p['id'])
command = ['docker','compose','exec','-T','mariadb','sh','-c','MYSQL_PWD="$MARIADB_PASSWORD" mariadb -u "$MARIADB_USER" "$MARIADB_DATABASE" -N -B']
counts = subprocess.check_output(command, input=sql, text=True).strip().splitlines()
assert counts == ['1','1'], counts
with urllib.request.urlopen(base+'/api/audit', timeout=10) as r: events=json.load(r)
events=[e for e in events if e['aggregateId']==p['id'] and e['eventType']=='PAYMENT_CREATED']
assert len(events)==1 and events[0]['eventId'] and events[0]['payload']['account']==p['account']
Path(output, 'persistence.json').write_text(json.dumps({'paymentId':p['id'],'paymentCount':1,'outboxCount':1,'auditEventId':events[0]['eventId'],'passed':True},indent=2))
print('One persisted payment, one outbox event and one correlated audit event verified')
