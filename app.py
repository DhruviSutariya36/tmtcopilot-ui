import os
import requests
from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Allowed file extensions
ALLOWED_EXTENSIONS = {"csv"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        category = request.form.get("category")
        description = request.form.get("description")
        file = request.files.get("file")

        # Validate inputs
        if not category or not description or not file:
            flash("All fields are required.")
            return redirect(url_for("index"))

        if not allowed_file(file.filename):
            flash("Only CSV files are allowed.")
            return redirect(url_for("index"))

        try:
            # Send file + data to Azure Function
            files = {"file": (secure_filename(file.filename), file.stream, "text/csv")}
            data = {"category": category, "description": description}

            response = requests.post(app.config["PARSE_FUNCTION_URL"], files=files, data=data)

            if response.status_code == 200:
                result = response.json()
                return render_template(
                    "form.html",
                    result=result,
                    download_url=app.config["AZURE_DOWNLOAD_FUNCTION_URL"],
                )
            else:
                flash(f"Azure Function error: {response.text}")
                return redirect(url_for("index"))

        except Exception as e:
            flash(f"Error: {str(e)}")
            return redirect(url_for("index"))

    # GET request → just render empty form
    return render_template("form.html")


if __name__ == "__main__":
    app.run(debug=True)
