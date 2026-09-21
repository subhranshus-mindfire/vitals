#!/usr/bin/env python3
"""
Test script to verify Azure Blob Storage connectivity, upload a sample 
clinical document, generate a secure SAS URL, and list container contents.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path so imports work cleanly
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load variables from .env file
load_dotenv(project_root / ".env")

def main():
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str or "DefaultEndpointsProtocol" not in conn_str:
        print("❌ Error: AZURE_STORAGE_CONNECTION_STRING is missing or empty in .env!")
        print("\nHow to get it:")
        print("1. Go to Azure Portal -> 'stvitalsdevcentralindia'")
        print("2. In the left menu, click 'Security + networking' -> 'Access keys'")
        print("3. Click 'Show' next to key1 -> Copy the 'Connection string'")
        print("4. Paste it into your .env file as:")
        print("   AZURE_STORAGE_CONNECTION_STRING=\"<your-connection-string>\"\n")
        sys.exit(1)

    try:
        from backend.services.storage_service import AzureBlobStorageService
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Please install requirements: pip install azure-storage-blob python-dotenv")
        sys.exit(1)

    print("=== Step 1: Connecting to Azure Blob Storage ===")
    service = AzureBlobStorageService()
    print(f"✅ Connected to container: '{service.container_name}'")

    # Step 2: Upload sample clinical document
    sample_file = project_root / "sample_data" / "patient_01_discharge_summary.txt"
    if not sample_file.exists():
        print(f"❌ Sample file not found at: {sample_file}")
        sys.exit(1)

    print(f"\n=== Step 2: Uploading '{sample_file.name}' ===")
    with open(sample_file, "rb") as f:
        file_bytes = f.read()

    blob_name = f"inbox/{sample_file.name}"
    blob_url = service.upload_document(
        blob_name=blob_name,
        data=file_bytes,
        content_type="text/plain",
        metadata={"patient_id": "PT-90214", "doc_type": "discharge_summary"}
    )
    print(f"✅ Uploaded successfully!")
    print(f"   Blob Path: {blob_name}")
    print(f"   Private URL: {blob_url}")

    # Step 3: Generate secure SAS URL
    print("\n=== Step 3: Generating Secure Temporary SAS URL (30 min validity) ===")
    sas_url = service.generate_sas_url(blob_name, expiry_minutes=30)
    print("✅ Secure SAS URL generated:")
    print(f"   {sas_url}")
    print("   👉 Notice: Anyone with this link can view the file, but it expires in 30 minutes!")

    # Step 4: List blobs in container
    print("\n=== Step 4: Listing All Blobs in 'clinical-documents' ===")
    blobs = service.list_documents()
    for b in blobs:
        print(f"   - 📄 {b['name']} ({b['size_bytes']} bytes, Last Modified: {b['last_modified']})")

    print("\n🎉 Milestone 2 Verification Complete! Azure Blob Storage is fully operational.")

if __name__ == "__main__":
    main()

