import os
import time
import logging
import requests
from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
from config import AZURE_DOWNLOAD_FUNCTION_URL, DURABLE_STARTER_URL

app = Flask(__name__)
app.config

ALLOWED_EXTENSIONS = {"csv"}

# Setup logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        category = request.form.get("category")
        description = request.form.get("description")
        file = request.files.get("file")

        if not category or not description or not file:
            flash("All fields are required.")
            return redirect(url_for("index"))

        if not allowed_file(file.filename):
            flash("Only CSV files are allowed.")
            return redirect(url_for("index"))

        try:
            files = {"file": (secure_filename(file.filename), file.stream, "text/csv")}
            data = {"category": category, "description": description}

            logging.info("Sending file to Durable Function starter...")
            response = requests.post(DURABLE_STARTER_URL, files=files, data=data)
            if response.status_code != 202:
                flash(f"Azure Function error: {response.text}")
                return redirect(url_for("index"))

            status_url = response.json().get("statusQueryGetUri")
            enriched_blob_url = None

            logging.info("Polling Durable Function for status...")
            while True:
                status_resp = requests.get(status_url)
                status_data = status_resp.json()
                runtime_status = status_data.get("runtimeStatus")
                logging.info(f"Current orchestration status: {runtime_status}")

                if runtime_status in ["Completed", "Failed", "Terminated"]:
                    break
                time.sleep(10)  # Poll every 10 seconds

            if runtime_status == "Completed":
                output = status_data.get("output", {})
                enriched_blob_url = output.get("enriched_blob_url")
                logging.info("Durable Function completed successfully.")
            else:
                flash(f"Durable Function failed with status: {runtime_status}")
                logging.error(f"Durable Function failed: {runtime_status}")
                return redirect(url_for("index"))

            return render_template(
                "form.html",
                result={"enriched_blob_url": enriched_blob_url, "filename": secure_filename(file.filename)}
            )

        except Exception as e:
            logging.error(f"Error during enrichment: {str(e)}", exc_info=True)
            flash(f"Error: {str(e)}")
            return redirect(url_for("index"))

    return render_template("form.html")

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
