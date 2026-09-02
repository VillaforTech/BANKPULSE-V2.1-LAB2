# ADR-XXX: Data Ownership de <servicio>

- **Estado:** Propuesto | Aceptado | Reemplazado
- **Fecha:** YYYY-MM-DD
- **Equipo:**

## Contexto
Describa la epica, bounded context y decisiones que obligan a definir ownership.

## Decision
Liste agregados y entidades canonicas que pertenecen al servicio.

## Source of Truth
Indique base/schema/coleccion y quien tiene permisos de escritura.

## Datos externos requeridos
Que informacion pertenece a otros servicios y como se obtiene.

## Integracion
REST, eventos, outbox, cache/proyeccion. Declare timeouts, idempotencia y comportamiento ante fallos.

## Consistencia
Clasifique cada flujo como fuerte o eventual y justifique.

## Seguridad y privacidad
Minimice datos duplicados; no replique informacion financiera o sensible sin necesidad.

## Observabilidad
Metricas, health checks, logs y alertas necesarias para demostrar la decision.

## Alternativas consideradas
Incluya al menos: base compartida, acceso directo a DB externa y otra tecnologia de persistencia.

## Consecuencias
### Positivas
### Negativas / trade-offs
