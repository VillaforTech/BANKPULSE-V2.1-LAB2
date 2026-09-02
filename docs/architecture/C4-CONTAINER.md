# C4 - Container View (texto de referencia)

```text
Socio / Operador
      |
      v
BankPulse Console + Edge Proxy (:8080)
      |
      +--> payments-api (:8081) ----------> MariaDB / bankpulse
      +--> audit-api (:8082) -------------> MongoDB / audit
      +--> experiences-api (:8083) -------> MongoDB / experiences
      +--> travel-benefits-api (:8084) ---> MongoDB / travel
      +--> events-api (:8085) ------------> PostgreSQL / events
      |                                      + Redis seat holds
      +--> social-split-api (:8086) ------> PostgreSQL / social_split

Prometheus (:9090) ---> /actuator/prometheus de los 6 servicios
Grafana (:3000) ------> Prometheus
cAdvisor (:8088) -----> Docker runtime metrics
```

Los puertos internos 8081-8086 no se publican fuera de Docker Compose. El edge `console` es el unico punto HTTP publicado para las APIs de negocio en el laboratorio.
