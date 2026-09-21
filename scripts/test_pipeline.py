#!/usr/bin/env python3
"""
Test script to verify the end-to-end extraction and validation pipeline:
1. Reads clinical documents (both Digital PDF, Scanned Image PDF, and TXT).
2. Extracts content using PDFExtractorService (Digital Text or Base64 Vision image).
3. Invokes AzureOpenAIExtractorService (GPT-4o Multimodal/Structured JSON).
4. Evaluates extracted values using ClinicWorksRulesEngine.
5. Displays formatted clinical report matching the Azure Assignment Web Dashboard.
"""

import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from backend.services.pdf_service import PDFExtractorService
from backend.services.ai_service import AzureOpenAIExtractorService
from backend.rules.engine import ClinicWorksRulesEngine


def run_test(filename: str):
    doc_path = project_root / "sample_data" / filename
    if not doc_path.exists():
        # Check if absolute path or direct relative path passed
        doc_path = Path(filename)
        if not doc_path.exists():
            print(f"❌ File not found: {filename}")
            return

    print(f"\n{'='*75}")
    print(f"📄 Processing Document: {doc_path.name}")
    print(f"{'='*75}")

    # Step 1: Extract Document Content (Digital text or Vision Base64)
    print("📑 Step 1: Processing Document via PDFExtractorService...")
    try:
        doc_input = PDFExtractorService.process_document(doc_path)
        if doc_input["format"] == "text":
            print(f"   Mode: Digital Text ({len(doc_input['content'])} characters extracted)")
        else:
            print(f"   Mode: Scanned / Image PDF (Base64 PNG generated for GPT-4o Vision, {len(doc_input['content'])} b64 chars)")
    except Exception as e:
        print(f"❌ Document extraction failed: {e}")
        return

    # Step 2: AI Extraction via Azure OpenAI (GPT-4o)
    ai_service = AzureOpenAIExtractorService()
    print(f"\n🤖 Step 2: Invoking Azure OpenAI (Model: {ai_service.deployment_name}, Mode: {ai_service.mode})...")

    if ai_service.mode == "unconfigured":
        print("❌ Error: Azure OpenAI credentials not configured in .env.")
        print("   Ensure AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are set.")
        return

    try:
        extraction = ai_service.extract(doc_input)
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return

    print("   AI Extraction Complete:")
    print(f"   • Patient ID:        {extraction.patient_id}")
    print(f"   • Patient Age:       {extraction.patient_age}")
    print(f"   • Document Type:     {extraction.document_type.value}")
    print(f"   • Is Clinical Doc:   {extraction.is_clinical_document}")
    print(f"   • Extraction Quality:{extraction.model_extraction_quality}")
    print(f"   • BP Candidates:     {len(extraction.bp_candidates)} found")
    for b in extraction.bp_candidates:
        flag = " [GOAL/HISTORICAL]" if b.is_goal_or_historical else ""
        print(f"       - {b.systolic}/{b.diastolic} mmHg (Date: {b.date}){flag} -> '{b.raw_snippet}'")
    print(f"   • A1C Candidates:    {len(extraction.a1c_candidates)} found")
    for a in extraction.a1c_candidates:
        flag = " [REF/TARGET]" if a.is_goal_or_historical else ""
        print(f"       - {a.value}% (Date: {a.date}){flag} -> '{a.raw_snippet}'")

    # Step 3: Business Rules Engine Evaluation
    print("\n🩺 Step 3: Evaluating Clinical Business Rules Engine...")
    engine = ClinicWorksRulesEngine()
    final_doc = engine.process(extraction, doc_path.name)

    # Step 4: Display Output Matching Azure Web App Dashboard
    status_icon = "✅" if final_doc.status.value == "Success" else ("⚠️" if final_doc.status.value == "Needs Review" else "❌")
    print("\n" + "—"*75)
    print("📋 CLINICWORKS DASHBOARD VIEW (Assignment Schema):")
    print("—"*75)
    print(f"  • Document Name:   {final_doc.document_name}")
    print(f"  • Document Type:   {final_doc.document_type.value}")
    print(f"  • Measure:         {final_doc.measure or 'None'}")
    print(f"  • Associated Date: {final_doc.associated_date or 'N/A'}")
    print(f"  • Status:          {status_icon} {final_doc.status.value}")
    print(f"  • Confidence Score:{final_doc.confidence_score:.2f}")
    print(f"  • Status Reason:   {final_doc.status_reason}")
    print(f"  • Action:          [ Retry Button Active ]")
    print("—"*75)


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "patient_01_discharge_summary.pdf"
    if target == "all":
        sample_dir = project_root / "sample_data"
        files = sorted([f.name for f in sample_dir.glob("*.pdf")])
        for f in files:
            run_test(f)
    else:
        run_test(target)


if __name__ == "__main__":
    main()
