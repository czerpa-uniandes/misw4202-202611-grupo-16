from flask import Flask
import redis
import json
import time
from datetime import datetime
import threading
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

REDIS_HOST = "redis"
HEARTBEAT_CHANNEL = "heartbeat"
TIMEOUT_SECONDS = 10

# Guardará último heartbeat recibido por servicio
services_last_seen = {}

service_status = Gauge("service_up", "Service availability", ["service_name"])

def clear_console():
    print("\033[H\033[J", end="")

def listen_heartbeats():
    r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
    pubsub = r.pubsub()
    pubsub.subscribe(HEARTBEAT_CHANNEL)

    print("Listening for heartbeats...\n")

    for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            service_id = data["service"]

            services_last_seen[service_id] = time.time()
            print(f"[Heartbeat recibido] {service_id}")

def monitor_services():
    while True:
        clear_console()

        # print("=======================================")
        # print("     INVENTORY SYSTEM MONITOR")
        # print("=======================================")
        # print(f"Last check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        # print("---------------------------------------")

        current_time = time.time()

        if not services_last_seen:
            print("No services registered yet...")
        else:
            for service, last_seen in services_last_seen.items():
                if current_time - last_seen <= TIMEOUT_SECONDS:
                    print(f"{service:<25} UP")
                    service_status.labels(service_name=service).set(1)
                else:
                    print(f"{service:<25} DOWN")
                    service_status.labels(service_name=service).set(0)

        print("---------------------------------------")
        time.sleep(5)

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain; version=0.0.4; charset=utf-8'}

if __name__ == "__main__":
    listener_thread = threading.Thread(target=listen_heartbeats, daemon=True)
    listener_thread.start()

    monitor_thread = threading.Thread(target=monitor_services, daemon=True)
    monitor_thread.start()

    app.run(host="0.0.0.0", port=5005)