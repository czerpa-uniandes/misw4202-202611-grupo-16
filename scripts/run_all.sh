#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

cleanup() {
  echo ""
  echo "Deteniendo servicios..."
  [[ -n "${CART_PID:-}" ]] && kill "$CART_PID" 2>/dev/null || true
  [[ -n "${ORDER_PID:-}" ]] && kill "$ORDER_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}

trap cleanup EXIT INT TERM

echo "Usando Python: $PYTHON_BIN"
echo "Iniciando cart_service en http://localhost:5001"
"$PYTHON_BIN" -m flask --app cart_service/app.py run --port=5001 > /tmp/cart_service.log 2>&1 &
CART_PID=$!

echo "Iniciando order_service en http://localhost:5002"
"$PYTHON_BIN" -m flask --app order_service/app.py run --port=5002 > /tmp/order_service.log 2>&1 &
ORDER_PID=$!

echo ""
echo "Servicios iniciados. Logs:"
echo "- /tmp/cart_service.log"
echo "- /tmp/order_service.log"
echo ""
echo "Prueba rápida:"
echo "- GET  http://localhost:5001/cart"
echo "- GET  http://localhost:5002/health"
echo ""
echo "Presiona Ctrl+C para detener todo."

wait
