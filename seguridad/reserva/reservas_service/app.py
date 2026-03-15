from __future__ import annotations

import json
import os
import time
from datetime import date
from typing import Any

import requests
from flask import Flask, Response, g, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import select

from database import SessionLocal, wait_for_db
from models import Habitacion, Reserva, SeguridadLog
from seed import init_schema_and_seed

app = Flask(__name__)

CLIENTES_SERVICE_URL = os.getenv("CLIENTES_SERVICE_URL", "http://clientes_service:5000")
TAX_RATE = float(os.getenv("TAX_RATE", "0.19"))
INIT_DB = os.getenv("INIT_DB", "false").lower() == "true"
TIMEOUT_SECONDS = 5

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
RESERVAS_CONFIRMADAS_TOTAL = Counter(
    "reservas_confirmadas_total",
    "Total de reservas confirmadas",
)
RESERVAS_MANIPULACIONES_DETECTADAS_TOTAL = Counter(
    "reservas_manipulaciones_detectadas_total",
    "Total de intentos de manipulación detectados",
)
RESERVAS_RECHAZADAS_TOTAL = Counter(
    "reservas_rechazadas_total",
    "Total de reservas rechazadas por validaciones",
    ["motivo"],
)


def bootstrap() -> None:
    global _bootstrapped
    if _bootstrapped:
        return
    wait_for_db()
    if INIT_DB:
        init_schema_and_seed()
    _bootstrapped = True


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except Exception as exc:
        raise ValueError(f"{field_name} debe tener formato YYYY-MM-DD") from exc


def _validate_cliente_activo(cliente_id: int) -> tuple[bool, str]:
    try:
        response = requests.get(
            f"{CLIENTES_SERVICE_URL}/clientes/{cliente_id}/status",
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        return False, f"error_consulta_clientes_service: {exc}"

    if response.status_code != 200:
        return False, "cliente_no_existe"

    body = response.json()
    if not body.get("active", False):
        return False, "cliente_inactivo"

    return True, "ok"


def _security_log(session: Any, cliente_id: int | None, payload: dict[str, Any], motivo: str) -> None:
    event = SeguridadLog(
        tipo_evento="INTENTO_MANIPULACION_FRONT",
        cliente_id=cliente_id,
        payload_recibido=json.dumps(payload, ensure_ascii=False),
        motivo=motivo,
    )
    print(f"[SECURITY] {motivo} payload={payload}")
    session.add(event)


@app.before_request
def startup() -> None:
    g.start_time = time.perf_counter()
    bootstrap()


@app.after_request
def metrics_after_request(response: Response) -> Response:
    endpoint = request.endpoint or request.path
    duration = time.perf_counter() - getattr(g, "start_time", time.perf_counter())
    HTTP_REQUESTS_TOTAL.labels(
        service="reservas_service",
        method=request.method,
        endpoint=endpoint,
        status=str(response.status_code),
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        service="reservas_service",
        method=request.method,
        endpoint=endpoint,
    ).observe(duration)
    return response


@app.get("/health")
def health() -> tuple[Any, int]:
    return jsonify({"status": "ok", "service": "reservas_service"}), 200


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.get("/inventario/<int:habitacion_id>")
def inventario(habitacion_id: int) -> tuple[Any, int]:
    with SessionLocal() as session:
        room = session.get(Habitacion, habitacion_id)
        if not room:
            return jsonify({"error": "habitacion_no_encontrada"}), 404
        return (
            jsonify(
                {
                    "id": room.id,
                    "nombre": room.nombre,
                    "precio_base": room.precio_base,
                    "disponible": room.disponible,
                }
            ),
            200,
        )


@app.post("/reservas/confirmar")
def confirmar_reserva() -> tuple[Any, int]:
    payload = request.get_json(silent=True) or {}

    required_fields = ["cliente_id", "habitacion_id", "fecha_inicio", "fecha_fin"]
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        RESERVAS_RECHAZADAS_TOTAL.labels(motivo="faltan_campos").inc()
        return jsonify({"error": "faltan_campos", "missing": missing_fields}), 400

    try:
        cliente_id = int(payload["cliente_id"])
        habitacion_id = int(payload["habitacion_id"])
        fecha_inicio = _parse_date(str(payload["fecha_inicio"]), "fecha_inicio")
        fecha_fin = _parse_date(str(payload["fecha_fin"]), "fecha_fin")
    except (TypeError, ValueError) as exc:
        RESERVAS_RECHAZADAS_TOTAL.labels(motivo="payload_invalido").inc()
        return jsonify({"error": "payload_invalido", "detail": str(exc)}), 400

    noches = (fecha_fin - fecha_inicio).days
    if noches <= 0:
        RESERVAS_RECHAZADAS_TOTAL.labels(motivo="rango_fechas_invalido").inc()
        return jsonify({"error": "rango_fechas_invalido"}), 400

    is_ok, reason = _validate_cliente_activo(cliente_id)
    if not is_ok:
        RESERVAS_RECHAZADAS_TOTAL.labels(motivo="cliente_no_valido").inc()
        return jsonify({"error": "cliente_no_valido", "detail": reason}), 400

    with SessionLocal() as session:
        try:
            with session.begin():
                room = session.execute(
                    select(Habitacion).where(Habitacion.id == habitacion_id).with_for_update()
                ).scalar_one_or_none()

                if not room:
                    RESERVAS_RECHAZADAS_TOTAL.labels(motivo="habitacion_no_encontrada").inc()
                    return jsonify({"error": "habitacion_no_encontrada"}), 404
                if not room.disponible:
                    RESERVAS_RECHAZADAS_TOTAL.labels(motivo="habitacion_no_disponible").inc()
                    return jsonify({"error": "habitacion_no_disponible"}), 409

                subtotal_calculado = round(room.precio_base * noches, 2)
                impuesto_calculado = round(subtotal_calculado * TAX_RATE, 2)
                total_calculado = round(subtotal_calculado + impuesto_calculado, 2)

                precio_front = payload.get("precio_enviado_front")
                impuesto_front = payload.get("impuesto_enviado_front")
                total_front = payload.get("total_enviado_front")

                mismatches: list[str] = []
                if precio_front is not None and round(float(precio_front), 2) != round(room.precio_base, 2):
                    mismatches.append("precio_enviado_front_no_coincide")
                if impuesto_front is not None and round(float(impuesto_front), 2) != impuesto_calculado:
                    mismatches.append("impuesto_enviado_front_no_coincide")
                if total_front is not None and round(float(total_front), 2) != total_calculado:
                    mismatches.append("total_enviado_front_no_coincide")

                if mismatches:
                    RESERVAS_MANIPULACIONES_DETECTADAS_TOTAL.inc()
                    _security_log(
                        session=session,
                        cliente_id=cliente_id,
                        payload=payload,
                        motivo=", ".join(mismatches),
                    )

                reserva = Reserva(
                    cliente_id=cliente_id,
                    habitacion_id=habitacion_id,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    subtotal_calculado=subtotal_calculado,
                    impuesto_calculado=impuesto_calculado,
                    total_calculado=total_calculado,
                    estado="confirmada",
                )
                session.add(reserva)
                session.flush()

                room.disponible = False
                reserva_id = reserva.id
                RESERVAS_CONFIRMADAS_TOTAL.inc()

            return (
                jsonify(
                    {
                        "reserva_id": reserva_id,
                        "estado": "confirmada",
                        "valores_front_ignorados": True,
                        "subtotal_calculado": subtotal_calculado,
                        "impuesto_calculado": impuesto_calculado,
                        "total_calculado": total_calculado,
                        "manipulacion_detectada": bool(mismatches),
                        "mismatch_detectados": mismatches,
                    }
                ),
                201,
            )
        except ValueError:
            RESERVAS_RECHAZADAS_TOTAL.labels(motivo="valores_numericos_invalidos_en_front").inc()
            return jsonify({"error": "valores_numericos_invalidos_en_front"}), 400


@app.get("/reservas")
def listar_reservas() -> tuple[Any, int]:
    with SessionLocal() as session:
        reservas = session.execute(select(Reserva)).scalars().all()
        body = [
            {
                "id": reserva.id,
                "cliente_id": reserva.cliente_id,
                "habitacion_id": reserva.habitacion_id,
                "fecha_inicio": reserva.fecha_inicio.isoformat(),
                "fecha_fin": reserva.fecha_fin.isoformat(),
                "subtotal_calculado": reserva.subtotal_calculado,
                "impuesto_calculado": reserva.impuesto_calculado,
                "total_calculado": reserva.total_calculado,
                "estado": reserva.estado,
            }
            for reserva in reservas
        ]
        return jsonify({"reservas": body}), 200


@app.get("/reservas/<int:reserva_id>")
def get_reserva(reserva_id: int) -> tuple[Any, int]:
    with SessionLocal() as session:
        reserva = session.get(Reserva, reserva_id)
        if not reserva:
            return jsonify({"error": "reserva_no_encontrada"}), 404

        return (
            jsonify(
                {
                    "id": reserva.id,
                    "cliente_id": reserva.cliente_id,
                    "habitacion_id": reserva.habitacion_id,
                    "fecha_inicio": reserva.fecha_inicio.isoformat(),
                    "fecha_fin": reserva.fecha_fin.isoformat(),
                    "subtotal_calculado": reserva.subtotal_calculado,
                    "impuesto_calculado": reserva.impuesto_calculado,
                    "total_calculado": reserva.total_calculado,
                    "estado": reserva.estado,
                }
            ),
            200,
        )


if __name__ == "__main__":
    bootstrap()
    app.run(host="0.0.0.0", port=5000)
