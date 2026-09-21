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

        # Step 2: Invoke Azure Function
        payload = {
            "document_name": filename,
            "blob_url": blob_url,
            "content_base64": content_base64
        }
        req = func.HttpRequest(body=json.dumps(payload).encode("utf-8"), method="POST")
        resp = extract_document(req)
        result_data = json.loads(resp.get_body().decode("utf-8"))

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

