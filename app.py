from flask import Flask, Response, request, render_template, send_file
from config import AZURE_DOWNLOAD_FUNCTION_URL, DURABLE_STARTER_URL
import requests
from io import BytesIO

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("form.html")

@app.route("/process", methods=["POST"])
def process():
    # Forward request to Azure Function
    files = {"file": request.files["file"]}
    data = {
        "system_description": request.form.get("system_description", ""),
        "compliance": request.form.get("compliance", "")
    }
    response = requests.post(DURABLE_STARTER_URL, files=files, data=data)
    return response.json()

@app.route("/download", methods=["GET"])
def download():
    blob_url = request.args.get("blob_url")
    filename = request.args.get("filename", "enriched.csv")  # default if not provided

    if not blob_url:
        return Response("Missing blob_url", status=400)

    try:
        # Call your Azure Function download-csv API
        download_api_url = AZURE_DOWNLOAD_FUNCTION_URL
        resp = requests.get(download_api_url, params={"blob_url": blob_url, "filename": filename}, stream=True)

        if resp.status_code != 200:
            return Response(f"Download failed: {resp.text}", status=resp.status_code)

        # Stream file to user browser
        return send_file(
            BytesIO(resp.content),
            as_attachment=True,
            download_name=filename,
            mimetype="text/csv"
        )
    except Exception as e:
        return Response(f"Error: {str(e)}", status=500)
