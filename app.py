from io import BytesIO
import time
import os
import logging
import requests
import math
from flask import Flask, request, jsonify, render_template, send_file

from config import AZURE_DOWNLOAD_FUNCTION_URL, DURABLE_STARTER_URL

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ----------------------
# Helper: sanitize JSON
# ----------------------
def sanitize_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_json(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, (int, str, bool)) or obj is None:
        return obj
    else:
        try:
            f = float(obj)
            return f if math.isfinite(f) else None
        except:
            return str(obj)

@app.route("/", methods=["GET"])
def upload_page():
    return render_template("form.html")


@app.route("/", methods=["POST"])
def start_enrichment():
    try:
        file = request.files.get("file")
        architecture = request.files.get("architecture")
        description = request.form.get("description", "")
        if not file:
            return jsonify({"error": "Missing file"}), 400

        files = {"csv_file": (file.filename, file.stream, file.mimetype)}
        if architecture:
            files["diagram_file"] = (architecture.filename, architecture.stream, architecture.mimetype)
        data = {
            "description": description,
            "category": request.form.get("category", "")
        }
        logging.info(f"Sending file {file.filename} to Durable Function")

        resp = requests.post(DURABLE_STARTER_URL, files=files, data=data, timeout=30)
        resp.raise_for_status()
        resp_json = sanitize_json(resp.json())

        if resp.status_code not in [200, 202]:
            return jsonify({"error": "Failed to start enrichment"}), 500

        return jsonify({
            "instanceId": resp_json.get("id"),
            "statusQueryGetUri": resp_json.get("statusQueryGetUri")
        })
    except Exception as e:
        logging.exception("Error in start_enrichment")
        return jsonify({"error": str(e)}), 500

@app.route("/download", methods=["GET"])
def download_csv():
    blob_url = request.args.get("blob_url")
    filename = request.args.get("filename", "download.csv")
    if not blob_url:
        return "Missing blob_url parameter", 400

    try:
        # Pass raw URL to Azure Function to avoid double encoding
        download_url = f"{AZURE_DOWNLOAD_FUNCTION_URL}?blob_url={blob_url}&filename={filename}"
        resp = requests.get(download_url, stream=True)
        resp.raise_for_status()
        return send_file(BytesIO(resp.content), as_attachment=True, download_name=filename, mimetype="text/csv")
    except Exception as e:
        logging.exception("Failed to download file")
        return f"Failed to download file: {e}", 500
    
if __name__ == "__main__":
    app.run(debug=True)
