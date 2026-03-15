from __future__ import annotations

import os
import time
from typing import Any

import requests
from flask import Flask, Response, g, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

app = Flask(__name__)

CLIENTES_SERVICE_URL = os.getenv("CLIENTES_SERVICE_URL", "http://clientes_service:5000")
RESERVAS_SERVICE_URL = os.getenv("RESERVAS_SERVICE_URL", "http://reservas_service:5000")
TIMEOUT_SECONDS = 5

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total de requests HTTP",
    ["service", "method", "endpoint", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Duración de requests HTTP en segundos",
    ["service", "method", "endpoint"],
)


def _forward_get(url: str) -> tuple[Any, int]:
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
        return jsonify(response.json()), response.status_code
    except requests.RequestException as exc:
        return jsonify({"error": "gateway_upstream_error", "detail": str(exc)}), 502


@app.before_request
def metrics_before_request() -> None:
    g.start_time = time.perf_counter()


@app.after_request
def metrics_after_request(response: Response) -> Response:
    endpoint = request.endpoint or request.path
    duration = time.perf_counter() - getattr(g, "start_time", time.perf_counter())
    HTTP_REQUESTS_TOTAL.labels(
        service="api_gateway",
        method=request.method,
        endpoint=endpoint,
        status=str(response.status_code),
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        service="api_gateway",
        method=request.method,
        endpoint=endpoint,
    ).observe(duration)
    return response


@app.get("/health")
def health() -> tuple[Any, int]:
    return jsonify({"status": "ok", "service": "api_gateway"}), 200


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.post("/gateway/reservas/confirmar")
def confirmar_reserva() -> tuple[Any, int]:
    payload = request.get_json(silent=True) or {}
    try:
        response = requests.post(
            f"{RESERVAS_SERVICE_URL}/reservas/confirmar",
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException as exc:
        return jsonify({"error": "gateway_upstream_error", "detail": str(exc)}), 502


@app.get("/gateway/reservas/<int:reserva_id>")
def obtener_reserva(reserva_id: int) -> tuple[Any, int]:
    return _forward_get(f"{RESERVAS_SERVICE_URL}/reservas/{reserva_id}")


@app.get("/gateway/reservas")
def listar_reservas() -> tuple[Any, int]:
    return _forward_get(f"{RESERVAS_SERVICE_URL}/reservas")


@app.get("/gateway/clientes/<int:cliente_id>")
def obtener_cliente(cliente_id: int) -> tuple[Any, int]:
    return _forward_get(f"{CLIENTES_SERVICE_URL}/clientes/{cliente_id}")


@app.get("/gateway/clientes")
def listar_clientes() -> tuple[Any, int]:
    return _forward_get(f"{CLIENTES_SERVICE_URL}/clientes")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
