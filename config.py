import os

class Config:
    # Flask secret key
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # Azure Functions
    DURABLE_STARTER_URL = os.getenv(
        "PARSE_FUNCTION_URL",
        "https://dev-tmtcopilot-func-bedma3g8buhnczbj.centralindia-01.azurewebsites.net/api/process"
    )
    AZURE_DOWNLOAD_FUNCTION_URL = os.getenv(
        "AZURE_DOWNLOAD_FUNCTION_URL",
        "https://dev-tmtcopilot-func-bedma3g8buhnczbj.centralindia-01.azurewebsites.net/api/download-csv"
    )
