# BankPulse Lab v2 - Codespaces

Esta version incorpora la correccion del Dev Container descubierta durante la validacion del laboratorio.

## Correccion Yarn

`.devcontainer/Dockerfile` parte de Java 21 Bookworm y elimina `/etc/apt/sources.list.d/yarn.list` antes de instalar las Features del Dev Container. Esto evita el fallo de APT/Yarn que podia dejar Codespaces en Recovery Mode y sin el comando `docker`.

## Validacion inicial

```bash
docker --version
docker compose version
java --version
mvn --version
```

Si Docker no existe, no instale Docker manualmente. Revise el Creation Log y reconstruya el Dev Container.

## BankPulse

```bash
docker compose config
docker compose up -d --build
docker compose ps
```

Abra el puerto 8080 desde la pestana Ports de Codespaces.

## Observabilidad

```bash
docker compose -f observability/compose.yaml config --services
docker compose -f observability/compose.yaml up -d
docker compose -f observability/compose.yaml ps
```

Servicios esperados: cAdvisor 8088, Prometheus 9090 y Grafana 3000.

Grafana del laboratorio: usuario `admin`; password `bankpulse_demo` (credencial exclusivamente academica).

## Apagado

```bash
docker compose -f observability/compose.yaml down
docker compose down
```
