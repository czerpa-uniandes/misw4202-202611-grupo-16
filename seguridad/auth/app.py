from flask import Flask, jsonify
import jwt
import datetime

app = Flask(__name__)

PRIVATE_KEY = open("/keys/private.pem").read()

@app.route("/login")
def login():

    payload = {
        "user_id": 101,
        "role": "cliente",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
    }

    token = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")

    return jsonify({"token": token})

app.run(host="0.0.0.0", port=5001)