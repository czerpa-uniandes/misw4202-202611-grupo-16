from flask import Flask, jsonify
import requests
import threading
import time
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

SERVICES = {
    "reservation": "http://reservation:5000/health",
}

service_status = Gauge("service_up", "Service availability", ["service_name"])

def monitor_services():
    while True:
        for name, url in SERVICES.items():
            try:
                r = requests.get(url, timeout=2)
                if r.status_code == 200:
                    service_status.labels(service_name=name).set(1)
                else:
                    service_status.labels(service_name=name).set(0)
            except:
                service_status.labels(service_name=name).set(0)
        time.sleep(5)

thread = threading.Thread(target=monitor_services)
thread.daemon = True
thread.start()

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain; version=0.0.4; charset=utf-8'}

@app.route("/health")
def health():
    return jsonify({"status": "monitor_alive"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)