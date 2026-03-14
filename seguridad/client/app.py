from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/clientes")

def clientes():

    clientes = [
        {"id":1,"nombre":"Juan"},
        {"id":2,"nombre":"Maria"}
    ]

    return jsonify(clientes)

app.run(host="0.0.0.0", port=5004)