import os
import time
import requests
from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

ALLOWED_EXTENSIONS = {"csv"}


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
            # 1. Call Durable Orchestrator starter function
            files = {"file": (secure_filename(file.filename), file.stream, "text/csv")}
            data = {"category": category, "description": description}

            response = requests.post(app.config["DURABLE_STARTER_URL"], files=files, data=data)

            if response.status_code != 202:
                flash(f"Azure Durable Function error: {response.text}")
                return redirect(url_for("index"))

            orchestration_info = response.json()
            status_url = orchestration_info["statusQueryGetUri"]

            # 2. Poll until orchestration completes
            result = None
            for _ in range(30):  # max ~30 polls
                status_resp = requests.get(status_url)
                status_json = status_resp.json()

                if status_json["runtimeStatus"] == "Completed":
                    result = status_json.get("output", {})
                    break
                elif status_json["runtimeStatus"] in ["Failed", "Terminated"]:
                    flash(f"Durable Function failed: {status_json}")
                    return redirect(url_for("index"))

                time.sleep(2)  # wait before next poll

            if result:
                return render_template(
                    "form.html",
                    result=result,
                    download_url=app.config["AZURE_DOWNLOAD_FUNCTION_URL"],
                )
            else:
                flash("Timeout waiting for Durable Function result.")
                return redirect(url_for("index"))

        except Exception as e:
            flash(f"Error: {str(e)}")
            return redirect(url_for("index"))

    return render_template("form.html")


if __name__ == "__main__":
    app.run(debug=True)
