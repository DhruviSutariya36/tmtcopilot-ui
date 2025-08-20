from flask import Flask, request, render_template, redirect, url_for
import requests

app = Flask(__name__)

# Configurable settings
app.config["DURABLE_START_URL"] = "http://localhost:7071/orchestrators/ProcessOrchestrator"  # Azure Function durable start endpoint
app.config["DOWNLOAD_FUNCTION_URL"] = "http://localhost:7071/api/download"  # Your download function

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("file")
        system_desc = request.form.get("system_desc")
        compliance = request.form.get("compliance")

        if not file:
            return render_template("form.html", error="Please upload a file.")

        # Prepare payload for Durable Function
        files = {"file": (file.filename, file.stream, file.mimetype)}
        data = {"system_desc": system_desc, "compliance": compliance}

        # Kick off Durable Orchestrator
        response = requests.post(app.config["DURABLE_START_URL"], files=files, data=data)

        if response.status_code == 202:
            result = response.json()
            status_url = result["statusQueryGetUri"]  # Durable Function status URL

            return render_template(
                "form.html",
                status_url=status_url,
                download_url=None,
                error=None,
            )
        else:
            return render_template("form.html", error="Error starting durable process.")

    return render_template("form.html")


@app.route("/status")
def check_status():
    """Check status of a Durable Function instance"""
    status_url = request.args.get("status_url")
    if not status_url:
        return redirect(url_for("index"))

    response = requests.get(status_url)
    if response.status_code == 200:
        status_data = response.json()
        runtime_status = status_data.get("runtimeStatus")
        output = status_data.get("output")

        if runtime_status == "Completed" and output:
            enriched_blob_url = output.get("enriched_blob_url")
            return render_template(
                "form.html",
                status_url=status_url,
                download_url=enriched_blob_url,
                error=None,
            )
        else:
            return render_template(
                "form.html",
                status_url=status_url,
                download_url=None,
                error=f"Still processing... Current status: {runtime_status}",
            )
    else:
        return render_template("form.html", error="Error checking status.")
