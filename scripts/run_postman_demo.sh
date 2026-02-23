#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COLLECTION="$ROOT_DIR/postman/Microservicios-Disponibilidad.postman_collection.json"
ENVIRONMENT="$ROOT_DIR/postman/Local.postman_environment.json"

if ! command -v newman >/dev/null 2>&1; then
  echo "No se encontró 'newman'."
  echo "Instálalo con: npm install -g newman"
  exit 1
fi

if [[ ! -f "$COLLECTION" || ! -f "$ENVIRONMENT" ]]; then
  echo "No se encontraron archivos de Postman en la carpeta esperada."
  exit 1
fi

echo "Ejecutando colección Postman con Newman..."
newman run "$COLLECTION" -e "$ENVIRONMENT" --reporters cli
