#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COLLECTION="$ROOT_DIR/postman/Microservicios-Disponibilidad.postman_collection.json"
ENVIRONMENT="$ROOT_DIR/postman/Local.postman_environment.json"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yaml"

ITERATIONS="${ITERATIONS:-50}"
DELAY_REQUEST_MS="${DELAY_REQUEST_MS:-100}"
FAIL_AFTER_SECONDS="${FAIL_AFTER_SECONDS:-5}"
DOWN_SECONDS="${DOWN_SECONDS:-10}"

cleanup() {
  docker compose -f "$COMPOSE_FILE" start cart_service >/dev/null 2>&1 || true
}

trap cleanup EXIT

if ! command -v newman >/dev/null 2>&1; then
  echo "No se encontró 'newman'."
  echo "Instálalo con: npm install -g newman"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "No se encontró 'docker'."
  exit 1
fi

if [[ ! -f "$COLLECTION" || ! -f "$ENVIRONMENT" ]]; then
  echo "No se encontraron archivos de Postman en la carpeta esperada."
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "No se encontró $COMPOSE_FILE"
  exit 1
fi

echo "Programando falla de cart_service: cae en ${FAIL_AFTER_SECONDS}s y vuelve en ${DOWN_SECONDS}s..."
(
  sleep "$FAIL_AFTER_SECONDS"
  echo "[experimento] Deteniendo cart_service..."
  docker compose -f "$COMPOSE_FILE" stop cart_service
  sleep "$DOWN_SECONDS"
  echo "[experimento] Iniciando cart_service..."
  docker compose -f "$COMPOSE_FILE" start cart_service
) &

echo "Ejecutando colección Postman con Newman..."
newman run "$COLLECTION" -e "$ENVIRONMENT" --reporters cli -n "$ITERATIONS" --delay-request "$DELAY_REQUEST_MS"
