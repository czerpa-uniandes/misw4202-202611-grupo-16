from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request
from prometheus_flask_exporter import PrometheusMetrics


# Permite importar el módulo compartido de cola desde la raíz del proyecto.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from shared_queue.file_queue import FileBackedQueue

app = Flask(__name__)
metrics = PrometheusMetrics(app)
metrics.info("cart_service_info", "Información del servicio cart", version="1.0.0")
queue_client = FileBackedQueue()

# Almacenamiento en memoria para el experimento didáctico.
cart_items: list[dict[str, Any]] = []


def _calculate_total(items: list[dict[str, Any]]) -> float:
    # Precios simplificados para no depender de un catálogo real.
    price_catalog = {"A001": 10.0, "B002": 25.5, "C003": 7.75}
    total = 0.0
    for item in items:
        unit_price = price_catalog.get(item["item_id"], 12.0)
        total += unit_price * item["quantity"]
    return round(total, 2)


@app.post("/cart/items")
def add_item() -> Any:
    payload = request.get_json(silent=True) or {}
    item_id = payload.get("item_id")
    quantity = payload.get("quantity")

    if not isinstance(item_id, str) or not item_id.strip():
        return jsonify({"error": "item_id must be a non-empty string"}), 400
    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"error": "quantity must be a positive integer"}), 400

    cart_items.append({"item_id": item_id.strip(), "quantity": quantity})
    return jsonify({"status": "item_added", "cart": cart_items}), 201


@app.get("/cart")
def get_cart() -> Any:
    return jsonify({"items": cart_items, "total": _calculate_total(cart_items)}), 200


@app.get("/health")
def health() -> Any:
    return jsonify({"status": "ok", "service": "cart_service"}), 200


@app.get("/echo")
def echo() -> Any:
    return jsonify({"echo": "pong", "service": "cart_service"}), 200


@app.post("/cart/checkout")
def checkout() -> Any:
    if not cart_items:
        return jsonify({"error": "cart is empty"}), 400

    order = {
        "order_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "items": list(cart_items),
        "total": _calculate_total(cart_items),
    }

    # Punto clave de arquitectura: publicación asíncrona en cola.
    # No hay llamada HTTP sincrónica a order_service.
    message_id = queue_client.enqueue(order)

    return (
        jsonify(
            {
                "status": "queued",
                "order_id": order["order_id"],
                "message_id": message_id,
            }
        ),
        202,
    )


if __name__ == "__main__":
    # Ejecución alternativa a flask run:
    # python app.py
    app.run(host="0.0.0.0", port=5001, debug=True)
