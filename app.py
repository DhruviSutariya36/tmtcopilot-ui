import tempfile
from flask import Flask, request, render_template, flash, redirect, send_file
from azure.storage.blob import BlobServiceClient
from werkzeug.utils import secure_filename
import os
import requests

app = Flask(__name__)
app.secret_key = "dev-secret-key"  

# Azure config
PARSE_FUNCTION_URL = "https://dev-tmtcopilot-func-bedma3g8buhnczbj.centralindia-01.azurewebsites.net/api/process?"
AZURE_DOWNLOAD_FUNCTION_URL = "https://dev-tmtcopilot-func-bedma3g8buhnczbj.centralindia-01.azurewebsites.net/api/download-csv"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("file")
        description = request.form.get("description")
        category = request.form.get("category")

        if not file or file.filename == "":
            flash("Please select a CSV file.")
            return redirect(request.url)

        if not file.filename.lower().endswith(".csv"):
            flash("Only CSV files are allowed.")
            return redirect(request.url)

        try:
            # Send to /process with metadata and file
            files = {
                "file": (secure_filename(file.filename), file.stream, "text/csv")
            }
            data = {
                "system_description": description,
                "compliance": category
            }

            response = requests.post(PARSE_FUNCTION_URL, data=data, files=files)

            try:
                result = response.json()
            except ValueError:
                flash("Invalid JSON response from backend.")
                return redirect(request.url)

            if response.status_code == 200:
                return render_template("form.html", result=result)
            else:
                flash(result.get("error", "Something went wrong."))
                return redirect(request.url)

        except Exception as e:
            flash(f"Upload error: {e}")
            return redirect(request.url)

    return render_template("form.html")

@app.route("/download", methods=["GET"])
def download_blob():
    blob_url = request.args.get("blob_url")
    if not blob_url:
        flash("Missing blob URL.")
        return redirect("/")

    # Extract filename from blob URL
    filename = blob_url.split("/")[-1]

    try:
        # Call Azure Function to download file
        resp = requests.get(f"{AZURE_DOWNLOAD_FUNCTION_URL}?filename={filename}")

        if resp.status_code != 200:
            flash("Download failed from Azure Function.")
            return redirect("/")

        # Save to a temp file to send
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(resp.content)
            tmp_path = tmp_file.name

        return send_file(tmp_path, as_attachment=True, download_name=filename, mimetype="text/csv")

    except Exception as e:
        flash(f"Error during download: {e}")
        return redirect("/")
    
if __name__ == "__main__":
    app.run(debug=True)