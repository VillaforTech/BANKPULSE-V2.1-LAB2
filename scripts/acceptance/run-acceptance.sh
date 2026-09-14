#!/usr/bin/env bash
# Orquesta las pruebas de aceptacion del issue #5:
#   1) business_test_social_split.py  (falso verde de extremo a extremo)
#   2) latency_benchmark.py           (tiempo real: latencia de N operaciones)
#   3) resilience_checks.py           (resiliencia: eventId, orden, broker, etc.)
#
# Convencion de exit codes de cada script (todos consistentes):
#   0 = PASS, 1 = FAIL de negocio, 2 = ERROR de entorno, 3 = SKIPPED (nunca verde)
#
# Este orquestador imprime una tabla resumen y decide el exit code global:
#   - exit 0 SOLO si business y benchmark obligatorios pasaron (exit 0) y
#     resilience no fallo (exit 0 o 3 son aceptables para resilience, porque
#     hoy el contrato que necesita todavia no existe -- ver issue #1/#4).
#   - Un SKIPPED (exit 3) en resilience NUNCA cuenta como verde: el exit
#     code global en ese caso es 3, no 0, para que CI no lo confunda con un
#     PASS real.
#   - Cualquier FAIL (1) o ERROR de entorno (2) en un obligatorio propaga
#     ese mismo codigo como resultado global.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
base_url="${BANKPULSE_URL:-http://localhost:8080}"
python_bin="${PYTHON_BIN:-python3}"

declare -a nombres=()
declare -a exit_codes=()

ejecutar() {
  local nombre="$1"
  shift
  echo ""
  echo "==================================================================="
  echo "==> Ejecutando: ${nombre}"
  echo "==================================================================="
  local codigo=0
  "$@" || codigo=$?
  nombres+=("$nombre")
  exit_codes+=("$codigo")
  echo "==> ${nombre} termino con exit code ${codigo}"
}

estado_de_codigo() {
  case "$1" in
    0) echo "PASS" ;;
    1) echo "FAIL" ;;
    2) echo "ERROR" ;;
    3) echo "SKIPPED" ;;
    *) echo "DESCONOCIDO(${1})" ;;
  esac
}

ejecutar "business_test_social_split" \
  "$python_bin" "$script_dir/business_test_social_split.py" --base-url "$base_url"

ejecutar "latency_benchmark" \
  "$python_bin" "$script_dir/latency_benchmark.py" --base-url "$base_url"

ejecutar "resilience_checks" \
  "$python_bin" "$script_dir/resilience_checks.py" --base-url "$base_url"

echo ""
echo "==================================================================="
echo "TABLA RESUMEN DE ACEPTACION (issue #5)"
echo "==================================================================="
printf "%-32s %-10s %-10s\n" "PRUEBA" "EXIT" "ESTADO"
resultado_global=0
business_ok=1
benchmark_ok=1
resilience_codigo=0

for i in "${!nombres[@]}"; do
  nombre="${nombres[$i]}"
  codigo="${exit_codes[$i]}"
  estado="$(estado_de_codigo "$codigo")"
  printf "%-32s %-10s %-10s\n" "$nombre" "$codigo" "$estado"

  case "$nombre" in
    business_test_social_split)
      if [ "$codigo" -ne 0 ]; then business_ok=0; fi
      ;;
    latency_benchmark)
      if [ "$codigo" -ne 0 ]; then benchmark_ok=0; fi
      ;;
    resilience_checks)
      resilience_codigo="$codigo"
      ;;
  esac
done

echo "-------------------------------------------------------------------"

# resilience_checks puede terminar en 3 (SKIPPED) sin que eso sea un fallo
# duro del harness -- hoy el contrato de eventos de Social Split no existe
# (issue #1/#4) -- pero SKIPPED nunca se reporta como PASS: si es el unico
# resultado no-cero, el exit code global sigue siendo 3, nunca 0.
if [ "$business_ok" -eq 0 ] || [ "$benchmark_ok" -eq 0 ]; then
  # Propagar el codigo mas severo entre los obligatorios que fallaron.
  resultado_global=1
  for i in "${!nombres[@]}"; do
    if [ "${exit_codes[$i]}" -eq 2 ]; then
      resultado_global=2
      break
    fi
  done
elif [ "$resilience_codigo" -eq 1 ] || [ "$resilience_codigo" -eq 2 ]; then
  resultado_global="$resilience_codigo"
elif [ "$resilience_codigo" -eq 3 ]; then
  resultado_global=3
else
  resultado_global=0
fi

echo ""
if [ "$resultado_global" -eq 0 ]; then
  echo "RESULTADO GLOBAL: PASS (exit 0)"
elif [ "$resultado_global" -eq 3 ]; then
  echo "RESULTADO GLOBAL: SKIPPED (exit 3) -- resilience depende del issue #1/#4; NO es verde"
elif [ "$resultado_global" -eq 2 ]; then
  echo "RESULTADO GLOBAL: ERROR DE ENTORNO (exit 2)"
else
  echo "RESULTADO GLOBAL: FAIL (exit 1)"
fi

exit "$resultado_global"
