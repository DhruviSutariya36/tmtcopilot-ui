import os
import time
import logging
import requests
from flask import Flask, jsonify, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
from config import AZURE_DOWNLOAD_FUNCTION_URL, DURABLE_STARTER_URL

app = Flask(__name__)
app.config

ALLOWED_EXTENSIONS = {"csv"}

# Setup logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["POST"])
def start_enrichment():
    file = request.files.get("file")
    category = request.form.get("category")
    description = request.form.get("description")

    if not file or not category or not description:
        return jsonify({"error": "All fields are required"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only CSV files are allowed"}), 400

    try:
        files = {"file": (secure_filename(file.filename), file.stream, "text/csv")}
        data = {"category": category, "description": description}

        # Call Durable Function starter
        response = requests.post(DURABLE_STARTER_URL, files=files, data=data)

        if response.status_code != 202:
            return jsonify({"error": response.text}), response.status_code

        # Return JSON as-is
        return jsonify(response.json()), 202

    except Exception as e:
        logging.error(f"Error starting enrichment: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

from flask import send_file, Response
import requests
import io

@app.route("/download", methods=["GET"])
def download():
    blob_url = request.args.get("blob_url")
    filename = request.args.get("filename")
    if not blob_url or not filename:
        flash("Missing blob URL or filename for download.")
        return redirect(url_for("index"))

    try:
        # Directly fetch blob content
        resp = requests.get(blob_url)
        if resp.status_code != 200:
            flash(f"Failed to download file from blob: {resp.status_code}")
            return redirect(url_for("index"))

        # Return as downloadable response
        return Response(
            resp.content,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )

    except Exception as e:
        flash(f"Download error: {str(e)}")
        return redirect(url_for("index"))

@app.route("/test")
def test():
    return "<h1>Hello, Flask UI is working!</h1>"

if __name__ == "__main__":
    app.run(debug=True)
