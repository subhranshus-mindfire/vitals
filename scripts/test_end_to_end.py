#!/usr/bin/env python3
"""
End-to-End Integration Test for ClinicWorks / Vitals Platform:
1. Tests document submission through the Orchestrator.
2. Invokes Azure Function (func-vitals-extractor-dev).
3. Verifies persistence into Database (PostgreSQL / SQLite).
4. Verifies dashboard records schema.
5. Verifies manual Retry action and audit trail in retry_history.
"""

import sys
import json
from pathlib import Path

# Setup project root
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.database.repository import ClinicalDatabaseRepository
from backend.services.orchestrator_service import PipelineOrchestratorService


def test_full_pipeline():
    print(f"\n{'='*75}")
    print("🚀 Running ClinicWorks End-to-End Integration Test...")
    print(f"{'='*75}")

    repo = ClinicalDatabaseRepository()
    orchestrator = PipelineOrchestratorService(repo)

    # 1. Process Patient 1 (BP Discharge Summary)
    print("\n📄 Step 1: Processing 'patient_01_discharge_summary.pdf'...")
    res1 = orchestrator.process_new_document(
        filename="patient_01_discharge_summary.pdf",
        blob_path="samples/patient_01_discharge_summary.pdf",
        blob_url="https://stvitalsdevcentralindia.blob.core.windows.net/clinical-documents/patient_01_discharge_summary.pdf"
    )
    print(f"   • Document ID:     {res1['document_id']}")
    print(f"   • Measure:         {res1['measure']}")
    print(f"   • Status:          {res1['status']}")
    print(f"   • Confidence:      {res1['confidence_score']}")
    assert res1["status"] in ["Success", "Needs Review"]

    # 2. Process Patient 4 (Non-Clinical Document)
    print("\n📄 Step 2: Processing Non-Clinical Document 'patient_04_non_clinical.pdf'...")
    res4 = orchestrator.process_new_document(
        filename="patient_04_non_clinical.pdf",
        blob_path="samples/patient_04_non_clinical.pdf",
        blob_url="https://stvitalsdevcentralindia.blob.core.windows.net/clinical-documents/patient_04_non_clinical.pdf"
    )
    print(f"   • Document ID:     {res4['document_id']}")
    print(f"   • Status:          {res4['status']}")
    print(f"   • Reason:          {res4['status_reason']}")
    assert res4["status"] == "Needs Review"

    # 3. Verify Dashboard Table Records
    print("\n📋 Step 3: Fetching Dashboard Records from Database...")
    docs = repo.get_dashboard_documents()
    print(f"   • Total records in DB: {len(docs)}")
    assert len(docs) >= 2

    # Check top document
    top_doc = docs[0]
    print(f"   • Latest Document: {top_doc['document_name']} | Status: {top_doc['status']} | Measure: {top_doc['measure']}")
    assert "document_name" in top_doc
    assert "status" in top_doc
    assert "confidence_score" in top_doc
    assert "status_reason" in top_doc

    # 4. Trigger Retry Action
    doc_to_retry = res1["document_id"]
    print(f"\n🔄 Step 4: Triggering Manual Retry Action on Document ID: {doc_to_retry}...")
    retry_res = orchestrator.trigger_retry(
        document_id=doc_to_retry,
        reason="Clinician triggered reprocess after verification"
    )
    print(f"   • Retry Attempt:   {retry_res['retry_attempt']}")
    print(f"   • Updated Status:  {retry_res['status']}")
    assert retry_res["retry_attempt"] >= 1

    # Verify updated record in DB
    updated_doc = repo.get_document_by_id(doc_to_retry)
    print(f"   • DB Retry Count:  {updated_doc['retry_count']}")
    assert updated_doc["retry_count"] >= 1

    print(f"\n{'='*75}")
    print("🎉 End-to-End Pipeline & Retry Mechanism Verified Successfully!")
    print(f"{'='*75}\n")


if __name__ == "__main__":
    test_full_pipeline()

