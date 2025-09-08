import os

# Flask secret key
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    # Azure Functions
DURABLE_STARTER_URL = os.getenv(
        "PARSE_FUNCTION_URL",
        "http://localhost:7071/api/process"
    )
AZURE_DOWNLOAD_FUNCTION_URL = os.getenv(
        "AZURE_DOWNLOAD_FUNCTION_URL",
        "httpp://localhost:7071/api/download-csv"
    )
