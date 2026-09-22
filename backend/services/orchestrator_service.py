"""
Orchestration Service for ClinicWorks / Vitals Platform.
Coordinates the workflow matching Azure Logic App (logic-vitals-pipeline-dev):
1. Ingestion / Upload event
2. Invocation of Azure Function (func-vitals-extractor-dev)
3. Persistence of results to Database (PostgreSQL / SQLite)
4. Execution of the Retry action with audit trail
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from backend.database.repository import ClinicalDatabaseRepository
from azure_function.function_app import extract_document, func


class PipelineOrchestratorService:
    """Coordinates document processing, Azure Function execution, database updates, and retries."""

    def __init__(self, repository: Optional[ClinicalDatabaseRepository] = None):
        self.repo = repository or ClinicalDatabaseRepository()

    def process_new_document(
        self,
        filename: str,
        blob_path: str,
        blob_url: str,
        content_base64: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the full pipeline for a newly submitted document:
        1. Register document in DB (status: 'uploaded')
        2. Invoke Azure Function extraction handler
        3. Save extraction result and status to DB (Success, Needs Review, or Failed)
        """
        # Step 1: Register document
        doc_id = self.repo.create_document(
            filename=filename,
            blob_path=blob_path,
            blob_url=blob_url
        )

    def _invoke_azure_function(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invokes the Azure Function either over HTTP (cloud) or in-memory (local fallback)."""
        func_url = os.getenv("AZURE_FUNCTION_URL", "https://func-vitals-extractor-dev.azurewebsites.net/api/extract")
        if func_url and (func_url.startswith("http://") or func_url.startswith("https://")):
            try:
                import urllib.request
                data = json.dumps(payload).encode("utf-8")
                req_obj = urllib.request.Request(
                    func_url,
                    data=data,
                    headers={"Content-Type": "application/json", "User-Agent": "ClinicWorks-WebDashboard"}
                )
                with urllib.request.urlopen(req_obj, timeout=45) as resp:
                with urllib.request.urlopen(req_obj, timeout=60) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception as ex:
                logging.warning(f"HTTP invocation to Azure Function ({func_url}) failed: {ex}. Attempting local fallback.")

        # Local in-process fallback
        try:
            from azure_function.function_app import extract_document, func
            req = func.HttpRequest(body=json.dumps(payload).encode("utf-8"), method="POST")
            req = func.HttpRequest(
                method="POST",
                url="http://localhost/api/extract",
                body=json.dumps(payload).encode("utf-8")
            )
            resp = extract_document(req)
            return json.loads(resp.get_body().decode("utf-8"))
        except Exception as local_ex:
            logging.error(f"Local in-process invocation failed: {local_ex}")
            return {
                "document_name": payload.get("document_name", "unknown"),
                "document_type": "UNKNOWN",
                "measure": None,
                "associated_date": None,
                "status": "Failed",
                "confidence_score": 0.0,
                "status_reason": f"Function execution error: {str(local_ex)}",
                "patient_id": None
            }

    def process_new_document(
        self,
        filename: str,
        blob_path: str,
        blob_url: str,
        content_base64: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the full pipeline for a newly submitted document:
        1. Register document in DB (status: 'uploaded')
        2. Invoke Azure Function extraction handler
        3. Save extraction result and status to DB (Success, Needs Review, or Failed)
        """
        # Step 1: Register document
        doc_id = self.repo.create_document(
            filename=filename,
            blob_path=blob_path,
            blob_url=blob_url
        )

        # Step 2: Invoke Azure Function
        payload = {
            "document_name": filename,
            "blob_url": blob_url,
            "content_base64": content_base64
        }
        req = func.HttpRequest(body=json.dumps(payload).encode("utf-8"), method="POST")
        resp = extract_document(req)
        result_data = json.loads(resp.get_body().decode("utf-8"))
        result_data = self._invoke_azure_function(payload)

        # Step 3: Persist processing result into Database
        self.repo.update_document_processing_result(
            document_id=doc_id,
            document_type=result_data.get("document_type", "UNKNOWN"),
            measure=result_data.get("measure"),
            associated_date=result_data.get("associated_date"),
            status=result_data.get("status", "Failed"),
            confidence_score=float(result_data.get("confidence_score", 0.0)),
            status_reason=result_data.get("status_reason"),
            patient_id=result_data.get("patient_id")
        )

        result_data["document_id"] = doc_id
        return result_data

    def trigger_retry(self, document_id: str, reason: str = "Clinician manual retry via dashboard") -> Dict[str, Any]:
        """
        Reprocesses an existing document (Retry Action):
        1. Increments retry count & records audit log in retry_history
        2. Re-invokes Azure Function
        3. Updates final status in database
        """
        doc = self.repo.get_document_by_id(document_id)
        if not doc:
            raise ValueError(f"Document ID {document_id} not found.")

        # Record retry attempt
        attempt_num = self.repo.record_retry(
            document_id=document_id,
            triggered_by="dashboard_clinician",
            reason=reason
        )

        # Re-invoke Azure Function
        payload = {
            "document_name": doc["filename"],
            "blob_url": doc["blob_url"]
        }
        req = func.HttpRequest(body=json.dumps(payload).encode("utf-8"), method="POST")
        resp = extract_document(req)
        result_data = json.loads(resp.get_body().decode("utf-8"))
        result_data = self._invoke_azure_function(payload)

        # Update document in database with latest result
        self.repo.update_document_processing_result(
            document_id=document_id,
            document_type=result_data.get("document_type", "UNKNOWN"),
            measure=result_data.get("measure"),
            associated_date=result_data.get("associated_date"),
            status=result_data.get("status", "Failed"),
            confidence_score=float(result_data.get("confidence_score", 0.0)),
            status_reason=result_data.get("status_reason"),
            patient_id=result_data.get("patient_id")
        )

        result_data["document_id"] = document_id
        result_data["retry_attempt"] = attempt_num
        return result_data

