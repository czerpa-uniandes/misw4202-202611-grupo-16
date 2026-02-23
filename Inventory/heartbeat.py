import os
import time
import json
import threading
import redis

# Leer ID de servicio desde variable de entorno
SERVICE_ID = os.getenv("SERVICE_ID", "inventory-default")

# Conexión a Redis
redis_client = redis.Redis(host="redis", port=6379)

def send_heartbeat():
    while True:
        heartbeat_message = {
            "service": SERVICE_ID
        }

        redis_client.publish("heartbeat", json.dumps(heartbeat_message))
        print(f"[Heartbeat] {SERVICE_ID} enviado")

        time.sleep(5)

def start_heartbeat():
    thread = threading.Thread(target=send_heartbeat, daemon=True)
    thread.start()