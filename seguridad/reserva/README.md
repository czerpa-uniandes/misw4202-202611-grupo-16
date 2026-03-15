# ASR-19 Experimento mínimo (seguridad e integridad)

Este experimento demuestra que:
- el frontend **no** define el precio final,
- el backend recalcula precio, impuestos y disponibilidad,
- si hay alteración, se detecta y se registra,
- la reserva se confirma solo con valores calculados en servidor.

## Arquitectura

Tres microservicios:
1. `api_gateway`: recibe peticiones externas y reenvía.
2. `clientes_service`: valida existencia/estado de cliente.
3. `reservas_service`: valida disponibilidad, recalcula montos, registra manipulación y confirma en transacción.

Base de datos: PostgreSQL.

## Estructura

- `docker-compose.yml`
- `api_gateway/`
- `clientes_service/`
- `reservas_service/`
- `scripts/curl_examples.sh`

## Endpoints mínimos

### API Gateway
- `POST /gateway/reservas/confirmar`
- `GET /gateway/reservas`
- `GET /gateway/reservas/<id>`
- `GET /gateway/clientes`
- `GET /gateway/clientes/<id>`

### Clientes
- `GET /clientes`
- `GET /clientes/<id>`
- `GET /clientes/<id>/status`

### Reservas
- `POST /reservas/confirmar`
- `GET /reservas`
- `GET /reservas/<id>`
- `GET /inventario/<room_id>`

## Reglas implementadas (ASR-19)

En `reservas_service`:
1. Nunca usa `precio_enviado_front`, `impuesto_enviado_front`, `total_enviado_front` para confirmar.
2. Siempre recalcula con datos servidor (precio_base, noches, impuesto).
3. Valida disponibilidad antes de confirmar.
4. Si hay diferencias, guarda evento en `seguridad_logs` con payload y motivo.
5. Confirma solo con valores calculados en backend, dentro de transacción.

## Tablas

- `clientes(id, nombre, email, activo)`
- `habitaciones(id, nombre, precio_base, disponible)`
- `reservas(id, cliente_id, habitacion_id, fecha_inicio, fecha_fin, subtotal_calculado, impuesto_calculado, total_calculado, estado)`
- `seguridad_logs(id, tipo_evento, cliente_id, payload_recibido, motivo, fecha)`

## Levantar el experimento

```bash
cd seguridad/reserva
docker compose up --build
```

Puertos:
- Gateway: `6010`
- Clientes: `6011`
- Reservas: `6012`
- PostgreSQL: `55432`
- Prometheus: `9091`

## Payload de prueba de ataque

```json
{
  "cliente_id": 1,
  "habitacion_id": 101,
  "fecha_inicio": "2026-03-20",
  "fecha_fin": "2026-03-23",
  "precio_enviado_front": 1000,
  "impuesto_enviado_front": 0,
  "total_enviado_front": 1000
}
```

## Escenarios

### 1) Caso normal
- Valores del frontend coinciden con cálculo backend.
- Respuesta: `201`, `manipulacion_detectada=false`.

### 2) Manipulación de precio
- Se envía `precio_enviado_front` alterado.
- Backend detecta diferencia, registra en `seguridad_logs` y confirma con total recalculado.

### 3) Manipulación de impuesto/total
- Se envía impuesto/total alterados.
- Backend ignora esos valores, registra evento y usa cálculo servidor.

## Pruebas rápidas con curl

```bash
cd seguridad/reserva
bash scripts/curl_examples.sh
```

## Verificación con Prometheus

1. Abre Prometheus en `http://localhost:9091`.
2. Ve a `Status > Targets` y valida que `api_gateway`, `clientes_service`, `reservas_service` estén en `UP`.
3. Ejecuta queries en `Graph`:

### Salud general
- `up`

### Tráfico HTTP por servicio
- `sum by (service) (http_requests_total)`
- `sum(rate(http_requests_total[1m])) by (service)`

### Latencia p95 por servicio/endpoint
- `histogram_quantile(0.95, sum by (le, service, endpoint) (rate(http_request_duration_seconds_bucket[5m])))`

### Evidencia ASR-19 (reservas)
- Reservas confirmadas: `reservas_confirmadas_total`
- Intentos detectados: `reservas_manipulaciones_detectadas_total`
- Rechazos por motivo: `sum by (motivo) (reservas_rechazadas_total)`
- Manipulaciones en ventana: `increase(reservas_manipulaciones_detectadas_total[10m])`
- Confirmaciones en ventana: `increase(reservas_confirmadas_total[10m])`

## Respuestas esperadas (resumen)

### Confirmación normal
- `estado: "confirmada"`
- `valores_front_ignorados: true`
- `manipulacion_detectada: false`

### Confirmación con manipulación
- `estado: "confirmada"`
- `valores_front_ignorados: true`
- `manipulacion_detectada: true`
- `mismatch_detectados` con campos alterados.

## Logs esperados en consola/BD

Con manipulación, `reservas_service` imprime:
- `[SECURITY] ... payload={...}`

Y en BD (`seguridad_logs`) se guarda:
- `tipo_evento = INTENTO_MANIPULACION_FRONT`
- `cliente_id`
- `payload_recibido`
- `motivo`
- `fecha`
