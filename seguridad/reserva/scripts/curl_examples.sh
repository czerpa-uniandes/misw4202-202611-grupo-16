#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:6010}"

echo "1) Validar cliente"
curl -s "$BASE_URL/gateway/clientes/1"

echo "2) Caso normal"
curl -s -X POST "$BASE_URL/gateway/reservas/confirmar" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": 1,
    "habitacion_id": 101,
    "fecha_inicio": "2026-03-20",
    "fecha_fin": "2026-03-23",
    "precio_enviado_front": 120000,
    "impuesto_enviado_front": 68400,
    "total_enviado_front": 428400
  }'

echo "3) Reiniciar experimento (dejar habitación disponible)"
docker compose down -v >/dev/null 2>&1 || true
docker compose up -d --build >/dev/null
sleep 5

echo "4) Caso manipulación de precio e impuesto"
curl -s -X POST "$BASE_URL/gateway/reservas/confirmar" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": 1,
    "habitacion_id": 101,
    "fecha_inicio": "2026-03-20",
    "fecha_fin": "2026-03-23",
    "precio_enviado_front": 1000,
    "impuesto_enviado_front": 0,
    "total_enviado_front": 1000
  }'

echo "5) Consultar reserva creada"
curl -s "$BASE_URL/gateway/reservas"

echo "6) Ver logs de seguridad desde PostgreSQL"
docker compose exec -T postgres psql -U asr19 -d asr19db -c "SELECT id,tipo_evento,cliente_id,motivo,fecha FROM seguridad_logs ORDER BY id DESC LIMIT 10;"
