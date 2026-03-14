from flask import Flask, request, jsonify
import jwt
import requests
import time

from prometheus_client import Counter, Histogram, start_http_server

app = Flask(__name__)

token_success = Counter(
    "token_validation_success_total",
    "Tokens validados correctamente"
)

token_failure = Counter(
    "token_validation_failure_total",
    "Tokens invalidados"
)

token_validation_total = Counter(
    "token_validation_total",
    "Total de tokens procesados"
)

token_latency = Histogram(
    "token_validation_latency_seconds",
    "Tiempo de validacion"
)

start_http_server(8000)

@app.route("/validar")

def validar():

    token = request.headers.get("Authorization")

    start = time.time()

    cert = requests.get("http://cert-service:5002/certificado").json()

    public_key = cert["public_key"]

    try:

        payload = jwt.decode(token, public_key, algorithms=["RS256"])

        token_success.inc()
        token_validation_total.inc()

        token_latency.observe(time.time() - start)

        return jsonify({
            "mensaje":"token valido",
            "usuario":payload
        })

    except jwt.InvalidTokenError:

        token_failure.inc()
        token_validation_total.inc()

        token_latency.observe(time.time() - start)

        return jsonify({
            "mensaje":"token invalido"
        }),401


app.run(host="0.0.0.0", port=5003)