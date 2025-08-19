from io import BytesIO
from flask import Flask, request, render_template, flash, redirect, send_file, url_for
from werkzeug.utils import secure_filename
import requests
import os
from config import Config

app = Flask(__name__)
app.config.from_object(Config)


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

            response = requests.post(app.config["PARSE_FUNCTION_URL"], data=data, files=files)

            try:
                result = response.json()
            except ValueError:
                flash("Invalid JSON response from backend.")
                return redirect(request.url)

            if response.status_code == 200:
                return render_template(
                    "form.html",
                    result=result,
                    download_url=url_for("download"),
                )
            else:
                flash(result.get("error", "Something went wrong."))
                return redirect(request.url)

        except Exception as e:
            flash(f"Upload error: {e}")
            return redirect(request.url)

    return render_template("form.html", download_url=url_for("download"))


@app.route("/download", methods=["GET"])
def download():
    blob_url = request.args.get("blob_url")
    if not blob_url:
        flash("Please provide Blob URL", "error")
        return redirect(url_for("index"))

    filename = os.path.basename(blob_url)
    params = {
        "blob_url": blob_url,
        "filename": filename
    }

    try:
        response = requests.get(app.config["AZURE_DOWNLOAD_FUNCTION_URL"], params=params)

        if response.status_code == 200:
            return send_file(
                BytesIO(response.content),
                as_attachment=True,
                download_name=filename,
                mimetype="text/csv"
            )
        else:
            flash(
                f"Download failed. Status code: {response.status_code}. Response: {response.text}",
                "error"
            )
            return redirect(url_for("index"))
    except Exception as e:
        flash(f"Error during download: {e}", "error")
        return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
