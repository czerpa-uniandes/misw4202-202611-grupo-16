from flask import Flask, jsonify

app = Flask(__name__)

PUBLIC_KEY = open("/keys/public.pem").read()

@app.route("/certificado")
def certificado():

    return jsonify({
        "public_key": PUBLIC_KEY
    })

app.run(host="0.0.0.0", port=5002)