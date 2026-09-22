#!/usr/bin/env python3
"""
Root entry point for Azure App Service Linux.
Supports:
1. Direct execution via python3 app.py (built-in HTTPServer)
2. WSGI execution via Gunicorn / Oryx (app / application callable)
"""

import os
import sys
import json
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app import run_server, repo, orchestrator, DASHBOARD_HTML


def application(environ, start_response):
    """Standard WSGI entry point for Gunicorn / Azure App Service."""
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET")

    # Handle CORS preflight
    if method == "OPTIONS":
        start_response("204 No Content", [
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type"),
        ])
        return []

    headers = [
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
        ("Access-Control-Allow-Headers", "Content-Type"),
    ]

    if method == "GET":
        if path == "/" or path == "/index.html":
            data = DASHBOARD_HTML.encode("utf-8")
            start_response("200 OK", headers + [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", str(len(data)))
            ])
            return [data]
        elif path == "/api/documents":
            docs = repo.get_dashboard_documents()
            data = json.dumps(docs).encode("utf-8")
            start_response("200 OK", headers + [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(data)))
            ])
            return [data]
        elif path == "/api/health":
            data = json.dumps({"status": "healthy", "service": "app-vitals-dev-centralindia-001"}).encode("utf-8")
            start_response("200 OK", headers + [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(data)))
            ])
            return [data]

    elif method == "POST":
        try:
            content_length = int(environ.get("CONTENT_LENGTH", 0))
        except (ValueError, TypeError):
            content_length = 0

        body_bytes = environ["wsgi.input"].read(content_length) if content_length > 0 else b"{}"
        data_json = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}

        if path == "/api/submit-sample":
            filename = data_json.get("filename", "patient_01_discharge_summary.pdf")
            blob_url = f"https://stvitalsdevcentralindia.blob.core.windows.net/clinical-documents/{filename}"
            res = orchestrator.process_new_document(
                filename=filename,
                blob_path=f"samples/{filename}",
                blob_url=blob_url
            )
            res_bytes = json.dumps(res).encode("utf-8")
            start_response("200 OK", headers + [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(res_bytes)))
            ])
            return [res_bytes]

        elif path == "/api/upload":
            filename = data_json.get("filename", "uploaded_file.pdf")
            content_base64 = data_json.get("content_base64")
            blob_url = f"https://stvitalsdevcentralindia.blob.core.windows.net/clinical-documents/{filename}"
            res = orchestrator.process_new_document(
                filename=filename,
                blob_path=f"uploads/{filename}",
                blob_url=blob_url,
                content_base64=content_base64
            )
            res_bytes = json.dumps(res).encode("utf-8")
            start_response("200 OK", headers + [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(res_bytes)))
            ])
            return [res_bytes]

        elif path.startswith("/api/documents/") and path.endswith("/retry"):
            parts = path.strip("/").split("/")
            doc_id = parts[2]
            res = orchestrator.trigger_retry(doc_id)
            res_bytes = json.dumps(res).encode("utf-8")
            start_response("200 OK", headers + [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(res_bytes)))
            ])
            return [res_bytes]

    start_response("404 Not Found", headers + [("Content-Type", "application/json")])
    return [b'{"error": "Not Found"}']


# Aliases for Azure Oryx / Gunicorn detection
app = application
wsgi_app = application

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    run_server(port)

