.PHONY: up down reset logs status smoke smoke-v2 obs-up obs-down obs-status all-up all-down chaos-mongo recover-mongo

up:
	docker compose up --build -d --wait

down:
	docker compose down

reset:
	docker compose -f observability/compose.yaml down -v || true
	docker compose down -v

logs:
	docker compose logs -f --tail=150

status:
	docker compose ps

smoke:
	bash scripts/smoke.sh

smoke-v2:
	bash scripts/smoke-v2.sh

obs-up:
	docker compose -f observability/compose.yaml up -d

obs-down:
	docker compose -f observability/compose.yaml down

obs-status:
	docker compose -f observability/compose.yaml ps

all-up: up obs-up

all-down: obs-down down

chaos-mongo:
	docker compose stop mongo audit-api

recover-mongo:
	docker compose up -d --wait mongo audit-api
