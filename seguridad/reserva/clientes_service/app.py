from __future__ import annotations

import time
from typing import Any

from flask import Flask, Response, g, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import select

from database import Base, SessionLocal, engine, wait_for_db
from models import Cliente

app = Flask(__name__)
_bootstrapped = False

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


def bootstrap() -> None:
    global _bootstrapped
    if _bootstrapped:
        return
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        has_clientes = session.execute(select(Cliente.id)).first() is not None
        if not has_clientes:
            session.add_all(
                [
                    Cliente(id=1, nombre="Ana Torres", email="ana@example.com", activo=True),
                    Cliente(id=2, nombre="Carlos Ruiz", email="carlos@example.com", activo=True),
                    Cliente(id=3, nombre="Cliente Inactivo", email="inactivo@example.com", activo=False),
                ]
            )
            session.commit()
    _bootstrapped = True


@app.before_request
def startup() -> None:
    g.start_time = time.perf_counter()
    bootstrap()


@app.after_request
def metrics_after_request(response: Response) -> Response:
    endpoint = request.endpoint or request.path
    duration = time.perf_counter() - getattr(g, "start_time", time.perf_counter())
    HTTP_REQUESTS_TOTAL.labels(
        service="clientes_service",
        method=request.method,
        endpoint=endpoint,
        status=str(response.status_code),
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        service="clientes_service",
        method=request.method,
        endpoint=endpoint,
    ).observe(duration)
    return response


@app.get("/health")
def health() -> tuple[Any, int]:
    return jsonify({"status": "ok", "service": "clientes_service"}), 200


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.get("/clientes/<int:cliente_id>")
def get_cliente(cliente_id: int) -> tuple[Any, int]:
    with SessionLocal() as session:
        cliente = session.get(Cliente, cliente_id)
        if not cliente:
            return jsonify({"error": "cliente_no_encontrado"}), 404

        return (
            jsonify(
                {
                    "id": cliente.id,
                    "nombre": cliente.nombre,
                    "email": cliente.email,
                    "activo": cliente.activo,
                }
            ),
            200,
        )


@app.get("/clientes")
def list_clientes() -> tuple[Any, int]:
    with SessionLocal() as session:
        clientes = session.execute(select(Cliente)).scalars().all()
        body = [
            {
                "id": cliente.id,
                "nombre": cliente.nombre,
                "email": cliente.email,
                "activo": cliente.activo,
            }
            for cliente in clientes
        ]
        return jsonify({"clientes": body}), 200


@app.get("/clientes/<int:cliente_id>/status")
def get_cliente_status(cliente_id: int) -> tuple[Any, int]:
    with SessionLocal() as session:
        cliente = session.get(Cliente, cliente_id)
        if not cliente:
            return jsonify({"exists": False, "active": False}), 404
        return jsonify({"exists": True, "active": cliente.activo}), 200


if __name__ == "__main__":
    bootstrap()
    app.run(host="0.0.0.0", port=5000)
