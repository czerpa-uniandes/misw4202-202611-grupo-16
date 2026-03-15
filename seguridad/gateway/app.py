from flask import Flask, request, Response
import time
from prometheus_client import Counter, start_http_server

app = Flask(__name__)

REQUEST_LIMIT = 30
WINDOW = 10

request_log = {}
blocked_ips = set()

blocked_counter = Counter(
    'blocked_ips_total',
    'Total de IPs bloqueadas'
)

ddos_counter = Counter(
    'ddos_detected_total',
    'Total de ataques DDoS detectados'
)


def detect_ddos(ip):

    now = time.time()

    if ip not in request_log:
        request_log[ip] = []

    request_log[ip] = [
        t for t in request_log[ip]
        if now - t < WINDOW
    ]

    request_log[ip].append(now)

    return len(request_log[ip]) > REQUEST_LIMIT


@app.route('/<path:path>', methods=["GET","POST"])
def gateway(path):

    ip = request.remote_addr

    if ip in blocked_ips:
        return Response("IP bloqueada", status=403)

    if detect_ddos(ip):

        blocked_ips.add(ip)

        ddos_counter.inc()
        blocked_counter.inc()

        print(f"Ataque detectado desde {ip}")

        return Response("Ataque detectado", status=403)

    return Response("Request aceptado", status=200)


if __name__ == "__main__":

    start_http_server(8000)

    app.run(host="0.0.0.0", port=5005)