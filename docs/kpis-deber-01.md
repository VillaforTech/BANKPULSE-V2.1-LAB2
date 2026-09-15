# KPIs del Deber 01

Social Split es dueño de la sesión. Estos indicadores describen compromisos de laboratorio, no cobros ni pérdidas reales. Los importes se calculan con `Decimal`/`BigDecimal` y cada moneda permanece separada.

## B-K1: cierres íntegros

En la ventana semiabierta `[now - 15 minutes, now)`, definida por `closedAt`:

`100 * cierres_validos / cierres_en_ventana`

Un cierre válido tiene al menos un participante, cuotas estrictamente positivas, suma exacta de cuotas igual a `totalAmount`, todos los participantes autorizados y referencias de pago no vacías. Si no hay cierres en la ventana, el resultado es `SIN MUESTRA`, no cero. `closedAt` se guarda una sola vez y fija la cohorte.

## B-K2: descuadre al cerrar

Para los cierres de la misma ventana de 15 minutos, por moneda:

`sum(abs(totalAmount - sum(cuotas_autorizadas)))`

La proyección conserva el hecho crudo y calcula el valor; el productor no envía un veredicto `valid`/`ok`. Una sesión inválida 60+30 sobre 100 produciría USD 10 si una mutación aislada la persistiera.

## B-K3: autorización sin resolución

En cada foto actual, sin limitar por la ventana de 15 minutos:

`sum(cuotas_autorizadas de sesiones OPEN con now - createdAt > staleOpenSeconds)`

El umbral predeterminado es `120` segundos y es configurable. La comparación es estrictamente `>`; no se inventan cierres ni se consulta la base de otro servicio.

## Cobertura temporal

Un Codespace limpio comienza a contar desde el primer evento producido por esta versión. Los datos anteriores requieren un snapshot público versionado y consistente; mientras no exista, la proyección debe declararse `INCOMPLETA`, no rellenarse con fechas de cierre retroactivas.