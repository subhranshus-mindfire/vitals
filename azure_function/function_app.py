"""
Azure Function App: func-vitals-extractor-dev
ClinicWorks / Vitals Platform Extraction & Clinical Business Rules Service.

Implements Azure Functions Python v2 programming model:
1. POST /api/extract:
   - Receives document reference (blob_url, blob_name, or content_base64)
   - Performs extraction via Azure OpenAI (GPT-4o)
   - Evaluates ClinicWorks Business Rules Engine
   - Returns standardized clinical measure, confidence score, and processing status
2. GET /api/health:
   - Health check and readiness probe
"""

import os
import sys
import json
import base64
import logging
import tempfile
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root is in sys.path for importing backend services
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

try:
    import azure.functions as func
except ImportError:
    # Graceful fallback mock for local testing without azure-functions package installed
    class MockHttpRequest:
        def __init__(self, body=b"", params=None, headers=None, method="POST"):
            self._body = body
            self.params = params or {}
            self.headers = headers or {}
            self.method = method

        def get_json(self):
            return json.loads(self._body.decode("utf-8")) if self._body else {}

        def get_body(self):
            return self._body

    class MockHttpResponse:
        def __init__(self, body="", status_code=200, mimetype="application/json"):
            self.body = body.encode("utf-8") if isinstance(body, str) else body
            self.status_code = status_code
            self.mimetype = mimetype

        def get_body(self):
            return self.body

    class MockFunctionApp:
        def __init__(self, *args, **kwargs):
            self.routes = {}

        def route(self, route: str, methods=None, auth_level=None):
            def decorator(f):
                self.routes[route] = f
                return f
            return decorator

    class func:
        FunctionApp = MockFunctionApp
        HttpRequest = MockHttpRequest
        HttpResponse = MockHttpResponse
        class AuthLevel:
            ANONYMOUS = "anonymous"
            FUNCTION = "function"

from backend.services.pdf_service import PDFExtractorService
from backend.services.ai_service import AzureOpenAIExtractorService
from backend.rules.engine import ClinicWorksRulesEngine
from backend.models.clinical import ProcessingOutcome, MeasureType

# Initialize Azure Functions App
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Readiness probe for Azure Logic App and monitoring services."""
    payload = {
        "status": "healthy",
        "service": "func-vitals-extractor-dev",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    }
    return func.HttpResponse(
        body=json.dumps(payload),
        status_code=200,
        mimetype="application/json"
    )


@app.route(route="extract", methods=["POST"])
def extract_document(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main extraction endpoint called by Azure Logic App.
    Accepts JSON:
    {
        "document_name": "patient_01_discharge_summary.pdf",
        "content_base64": "<optional base64 encoded document bytes>",
        "blob_url": "<optional SAS URL or direct blob url>",
        "blob_name": "<optional blob name in container>"
    }
    """
    logging.info("⚡ func-vitals-extractor-dev: Received document extraction request.")

    try:
        req_data = req.get_json()
    except Exception as e:
        error_resp = {
            "document_name": "unknown",
            "document_type": MeasureType.UNKNOWN.value,
            "measure": None,
            "associated_date": None,
            "status": ProcessingOutcome.FAILED.value,
            "confidence_score": 0.0,
            "status_reason": f"Invalid JSON payload: {str(e)}",
            "patient_id": None,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        return func.HttpResponse(
            body=json.dumps(error_resp),
            status_code=400,
            mimetype="application/json"
        )

    document_name = req_data.get("document_name", "unnamed_document.pdf")
    content_base64 = req_data.get("content_base64")
    blob_url = req_data.get("blob_url")
    blob_name = req_data.get("blob_name")

    temp_path = None
    try:
        # Step 1: Resolve document content
        suffix = Path(document_name).suffix or ".pdf"
        
        if content_base64:
            # Document provided directly as Base64 bytes
            doc_bytes = base64.b64decode(content_base64)
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(doc_bytes)
                temp_path = tmp.name
        elif blob_url and "?" in blob_url:
            # Download via provided authenticated SAS URL
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                req_obj = urllib.request.Request(blob_url, headers={"User-Agent": "func-vitals-extractor-dev"})
                with urllib.request.urlopen(req_obj) as resp:
                    tmp.write(resp.read())
                temp_path = tmp.name
        else:
            # Fallback 1: Local sample data if present
            local_sample = project_root / "sample_data" / document_name
            if local_sample.exists():
                temp_path = str(local_sample)
            elif os.getenv("AZURE_STORAGE_CONNECTION_STRING") and (blob_name or document_name):
                # Fallback 2: Download securely from Blob Storage using storage service credentials
                try:
                    from backend.services.storage_service import AzureBlobStorageService
                    storage_service = AzureBlobStorageService()
                    target_name = blob_name or document_name
                    blob_client = storage_service.container_client.get_blob_client(target_name)
                    doc_bytes = blob_client.download_blob().readall()
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                        tmp.write(doc_bytes)
                        temp_path = tmp.name
                except Exception as ex:
                    raise RuntimeError(f"Unable to retrieve document from Azure Blob Storage: {ex}")
            else:
                raise ValueError(f"Unable to access document '{document_name}'. Provide valid content_base64 or SAS URL.")

        # Step 2: Extract text or vision image via PDFExtractorService
        doc_input = PDFExtractorService.process_document(temp_path)

        # Step 3: Run AI extraction via Azure OpenAI GPT-4o
        ai_service = AzureOpenAIExtractorService()
        if ai_service.mode == "unconfigured":
            raise RuntimeError("Azure OpenAI service credentials not configured in environment.")

        extraction = ai_service.extract(doc_input)

        # Step 4: Run ClinicWorks Clinical Business Rules Engine
        rules_engine = ClinicWorksRulesEngine()
        final_doc = rules_engine.process(extraction, document_name)

        # Step 5: Format response matching the 7 assignment fields
        response_payload = {
            "document_name": final_doc.document_name,
            "document_type": final_doc.document_type.value,
            "measure": final_doc.measure,
            "associated_date": final_doc.associated_date,
            "status": final_doc.status.value,
            "confidence_score": final_doc.confidence_score,
            "status_reason": final_doc.status_reason,
            "patient_id": final_doc.patient_id,
            "processed_at": final_doc.processed_at.isoformat()
        }

        return func.HttpResponse(
            body=json.dumps(response_payload),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error processing document {document_name}: {e}")
        error_payload = {
            "document_name": document_name,
            "document_type": MeasureType.UNKNOWN.value,
            "measure": None,
            "associated_date": None,
            "status": ProcessingOutcome.FAILED.value,
            "confidence_score": 0.0,
            "status_reason": f"Technical processing error: {str(e)}",
            "patient_id": None,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        return func.HttpResponse(
            body=json.dumps(error_payload),
            status_code=200,  # Return 200 with 'Failed' status so Logic App can record state & trigger retry
            mimetype="application/json"
        )

    finally:
        # Cleanup temporary file if created
        if temp_path and os.path.exists(temp_path) and "sample_data" not in temp_path:
            try:
                os.remove(temp_path)
            except Exception:
                pass

