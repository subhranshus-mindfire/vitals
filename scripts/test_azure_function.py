#!/usr/bin/env python3
"""
Test script to verify Azure Function App (func-vitals-extractor-dev) handler:
Simulates Azure Logic App invoking the Azure Function endpoints:
1. GET /api/health - Readiness probe
2. POST /api/extract - Digital PDF payload
3. POST /api/extract - Base64 encoded document payload
4. POST /api/extract - Non-clinical document (Needs Review outcome)
"""

import sys
import json
import base64
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from azure_function.function_app import app, health_check, extract_document


def mock_request(body_dict: dict = None, method: str = "POST"):
    """Creates a mock HttpRequest matching Azure Functions spec."""
    from azure_function.function_app import func
    body_bytes = json.dumps(body_dict).encode("utf-8") if body_dict is not None else b""
    return func.HttpRequest(body=body_bytes, method=method)


def test_health():
    print(f"\n{'='*75}")
    print("🔍 Testing Azure Function Endpoint: GET /api/health")
    print(f"{'='*75}")
    req = mock_request(method="GET")
    resp = health_check(req)
    data = json.loads(resp.get_body().decode("utf-8"))
    print(f"Status Code: {resp.status_code}")
    print(f"Response:    {json.dumps(data, indent=2)}")
    assert resp.status_code == 200
    assert data["status"] == "healthy"
    print("✅ Health probe passed!")


def test_extract_digital_pdf():
    print(f"\n{'='*75}")
    print("📄 Testing Azure Function Endpoint: POST /api/extract (Digital PDF)")
    print(f"{'='*75}")
    req = mock_request({
        "document_name": "patient_01_discharge_summary.pdf"
    })
    resp = extract_document(req)
    data = json.loads(resp.get_body().decode("utf-8"))
    print(f"Status Code: {resp.status_code}")
    print("📋 Azure Function Result:")
    for k, v in data.items():
        print(f"   • {k:18}: {v}")
    
    assert resp.status_code == 200
    assert data["document_type"] == "BP"
    assert data["status"] in ["Success", "Needs Review"]
    print("✅ Digital PDF extraction via Azure Function passed!")


def test_extract_base64_payload():
    print(f"\n{'='*75}")
    print("📦 Testing Azure Function Endpoint: POST /api/extract (Base64 Payload)")
    print(f"{'='*75}")
    sample_file = project_root / "sample_data" / "patient_02_outpatient_visit.pdf"
    with open(sample_file, "rb") as f:
        b64_content = base64.b64encode(f.read()).decode("utf-8")

    req = mock_request({
        "document_name": "patient_02_outpatient_visit.pdf",
        "content_base64": b64_content
    })
    resp = extract_document(req)
    data = json.loads(resp.get_body().decode("utf-8"))
    print(f"Status Code: {resp.status_code}")
    print("📋 Azure Function Result:")
    for k, v in data.items():
        print(f"   • {k:18}: {v}")

    assert resp.status_code == 200
    assert data["status"] in ["Success", "Needs Review"]
    print("✅ Base64 document payload via Azure Function passed!")


def test_extract_non_clinical():
    print(f"\n{'='*75}")
    print("⚠️ Testing Azure Function Endpoint: POST /api/extract (Non-Clinical)")
    print(f"{'='*75}")
    req = mock_request({
        "document_name": "patient_04_non_clinical.pdf"
    })
    resp = extract_document(req)
    data = json.loads(resp.get_body().decode("utf-8"))
    print(f"Status Code: {resp.status_code}")
    print("📋 Azure Function Result:")
    for k, v in data.items():
        print(f"   • {k:18}: {v}")

    assert resp.status_code == 200
    assert data["status"] == "Needs Review"
    print("✅ Non-clinical handling via Azure Function passed!")


def main():
    print("⚡ Starting Azure Function Local Verification Suite...")
    test_health()
    test_extract_digital_pdf()
    test_extract_base64_payload()
    test_extract_non_clinical()
    print(f"\n{'='*75}")
    print("🎉 All Azure Function tests PASSED successfully!")
    print(f"{'='*75}")


if __name__ == "__main__":
    main()

