from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Any

from flask import Flask, jsonify
from prometheus_flask_exporter import PrometheusMetrics


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from order_service.order_store import OrderStore
from order_service.worker import OrderWorker
from shared_queue.file_queue import FileBackedQueue

app = Flask(__name__)
metrics = PrometheusMetrics(app)
metrics.info("order_service_info", "Información del servicio order", version="1.0.0")
queue_client = FileBackedQueue()
order_store = OrderStore()

worker_lock = threading.Lock()
worker_started = False
worker: OrderWorker | None = None


def _process_order(order: dict[str, Any]) -> None:
    # Simula la “creación” de la orden al persistirla como procesada.
    order_store.add_order(order)
    print(f"[order_service] Orden procesada: {order['order_id']}")


def _ensure_worker_started() -> None:
    global worker_started, worker
    if worker_started:
        return

    with worker_lock:
        if worker_started:
            return

        # Punto clave de arquitectura: este worker consume la cola en segundo plano.
        # Si el servicio estuvo caído, al volver procesa backlog pendiente.
        worker = OrderWorker(
            poll_fn=queue_client.dequeue,
            process_fn=_process_order,
            ack_fn=queue_client.ack,
            interval_seconds=1.0,
        )
        worker.start()
        worker_started = True


@app.before_request
def boot_worker() -> None:
    _ensure_worker_started()


@app.get("/orders")
def list_orders() -> Any:
    return jsonify({"orders": order_store.list_orders()}), 200


@app.get("/health")
def health() -> Any:
    return jsonify({"status": "ok", "worker_started": worker_started}), 200


@app.get("/echo")
def echo() -> Any:
    return jsonify({"echo": "pong", "service": "order_service"}), 200


if __name__ == "__main__":
    _ensure_worker_started()
    app.run(host="0.0.0.0", port=5002, debug=True)
