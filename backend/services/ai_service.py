"""
Azure OpenAI Extraction Service for ClinicWorks Platform.

Uses Azure OpenAI (GPT-4o) with Structured JSON Output
to classify clinical documents and accurately extract Blood Pressure (BP) and HbA1c values.
Supports:
1. Text documents and Digital PDFs.
2. Scanned / Image-Based PDFs via Multimodal Vision (Base64 PNG).
3. Structured JSON extraction for Blood Pressure (BP) and HbA1c (A1C).
"""

import json
import os
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List, Union

from backend.models.clinical import (
    ClinicalExtractionResult,
    MeasureType,
    BPReadingCandidate,
    A1CReadingCandidate,
)

SYSTEM_PROMPT = """You are a specialized clinical quality measure extraction engine for ClinicWorks.
Your job is to analyze clinical documents (both digital text and scanned medical images)
and extract quality measure data strictly adhering to clinical rules.

MEASURES SUPPORTED:
1. Blood Pressure (BP)
2. HbA1c (A1C)

INSTRUCTIONS:
1. Document Measure Type:
   - Classify document_type as strictly one of: "BP", "A1C", or "UNKNOWN".
   - If the document is non-clinical (invoice, receipt, general memo), set is_clinical_document to false.

2. Patient Demographics:
   - Extract patient_id if present (e.g., PT-90214).
   - Extract patient_age (integer years) if explicitly mentioned (e.g. 58, 17, 42).

3. Blood Pressure Candidates (BP):
   - Locate all blood pressure readings in the document.
   - For EACH reading, extract systolic and diastolic integers.
   - Extract the associated date if written (YYYY-MM-DD or as stated).
   - CRITICAL: Flag is_goal_or_historical as TRUE if the reading is described as a "goal BP", "target BP", "past BP", "previous BP", or reference standard.
   - Flag is_goal_or_historical as FALSE for current, actual patient measurements.

4. HbA1c Candidates (A1C):
   - Locate all Glycated Hemoglobin / HbA1c readings.
   - For EACH reading, extract the numeric value (e.g. 7.4, 5.7).
   - Extract the specimen collection date if stated.
   - CRITICAL: Flag is_goal_or_historical as TRUE if the value is a reference range (e.g. "< 5.7% is normal"), target goal, or historical example.
   - Flag is_goal_or_historical as FALSE for actual patient lab results.

5. Model Quality:
   - Provide a model_extraction_quality score between 0.0 and 1.0 based on legibility and certainty.
   - Do NOT invent or hallucinate values.
   - Return valid JSON matching the following schema:
{
  "patient_id": "PT-...",
  "patient_age": 58,
  "document_type": "BP" | "A1C" | "UNKNOWN",
  "is_clinical_document": true,
  "bp_candidates": [
    {
      "systolic": 138,
      "diastolic": 88,
      "date": "2026-03-14",
      "is_goal_or_historical": false,
      "raw_snippet": "BP: 138/88 mmHg"
    }
  ],
  "a1c_candidates": [
    {
      "value": 7.4,
      "date": "2026-03-14",
      "is_goal_or_historical": false,
      "raw_snippet": "HbA1c: 7.4%"
    }
  ],
  "model_extraction_quality": 0.95,
  "raw_observations": "summary notes"
}
"""


class AzureOpenAIExtractorService:
    """Service to communicate with Azure OpenAI for clinical document extraction."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment_name: Optional[str] = None,
        api_version: str = "2024-02-15-preview",
    ):
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment_name = deployment_name or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        self.mode = "unconfigured"

        self._initialize_client()

    def _initialize_client(self):
        """Initializes the Azure OpenAI client via SDK or native REST fallback."""
        if not (self.endpoint and self.api_key) and not self.openai_api_key:
            self.client = None
            self.mode = "unconfigured"
            return

        try:
            from openai import AzureOpenAI, OpenAI

            if self.endpoint and self.api_key:
                self.client = AzureOpenAI(
                    azure_endpoint=self.endpoint,
                    api_key=self.api_key,
                    api_version=self.api_version,
                )
                self.mode = "azure_sdk"
            elif self.openai_api_key:
                self.client = OpenAI(api_key=self.openai_api_key)
                self.mode = "standard_openai_sdk"
        except ImportError:
            # Fallback to standard library urllib REST client (zero external pip packages needed)
            if self.endpoint and self.api_key:
                self.client = "native_urllib"
                self.mode = "azure_rest"
            elif self.openai_api_key:
                self.client = "native_urllib"
                self.mode = "standard_openai_rest"

    def extract(self, document_input: Union[Dict[str, Any], str]) -> ClinicalExtractionResult:
        """
        Extracts clinical biomarkers and document classification using LLM.
        Supports both official openai SDK and native Python urllib.
        
        Args:
            document_input: Either raw text string OR dict with keys:
                - 'format': 'text' or 'image_base64'
                - 'content': raw text string OR base64-encoded PNG string
        """
        if self.mode == "unconfigured":
            raise RuntimeError(
                "Azure OpenAI credentials not configured. "
                "Ensure AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are configured in .env."
            )

        if isinstance(document_input, str):
            fmt = "text"
            content_data = document_input
        else:
            fmt = document_input.get("format", "text")
            content_data = document_input.get("content", "")

        # Build message payload (text or multimodal vision)
        if fmt == "image_base64":
            user_content = [
                {
                    "type": "text",
                    "text": "Please analyze this scanned clinical document image and extract the quality measure (BP or A1C):"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{content_data}"
                    }
                }
            ]
        else:
            user_content = [
                {
                    "type": "text",
                    "text": f"Please analyze this clinical document and extract the quality measure (BP or A1C):\n\n{content_data}"
                }
            ]

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        if self.mode.endswith("_sdk"):
            model_name = self.deployment_name if "azure" in self.mode else "gpt-4o"
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            raw_json_str = response.choices[0].message.content
        else:
            # Native urllib REST call
            url = f"{self.endpoint.rstrip('/')}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            payload = {
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": 0.0
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            try:
                with urllib.request.urlopen(req) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    raw_json_str = resp_data["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8")
                raise RuntimeError(f"Azure OpenAI REST API call failed (HTTP {e.code}): {error_body}")
            except Exception as e:
                raise RuntimeError(f"Azure OpenAI request failed: {e}")

        parsed_json = json.loads(raw_json_str)

        # Parse BP candidates
        bp_candidates: List[BPReadingCandidate] = []
        for r in parsed_json.get("bp_candidates", []):
            if isinstance(r, dict):
                bp_candidates.append(BPReadingCandidate(
                    systolic=r.get("systolic"),
                    diastolic=r.get("diastolic"),
                    date=r.get("date"),
                    is_goal_or_historical=r.get("is_goal_or_historical", False),
                    raw_snippet=r.get("raw_snippet"),
                ))

        # Parse A1C candidates
        a1c_candidates: List[A1CReadingCandidate] = []
        for r in parsed_json.get("a1c_candidates", []):
            if isinstance(r, dict):
                a1c_candidates.append(A1CReadingCandidate(
                    value=r.get("value"),
                    date=r.get("date"),
                    is_goal_or_historical=r.get("is_goal_or_historical", False),
                    raw_snippet=r.get("raw_snippet"),
                ))

        # Document Type classification
        doc_type_raw = str(parsed_json.get("document_type", "UNKNOWN")).upper()
        if "BP" in doc_type_raw:
            doc_type = MeasureType.BP
        elif "A1C" in doc_type_raw or "HBA1C" in doc_type_raw:
            doc_type = MeasureType.A1C
        else:
            doc_type = MeasureType.UNKNOWN

        return ClinicalExtractionResult(
            patient_id=parsed_json.get("patient_id"),
            patient_age=parsed_json.get("patient_age"),
            document_type=doc_type,
            is_clinical_document=parsed_json.get("is_clinical_document", True),
            bp_candidates=bp_candidates,
            a1c_candidates=a1c_candidates,
            model_extraction_quality=float(parsed_json.get("model_extraction_quality", 0.95)),
            raw_observations=parsed_json.get("raw_observations"),
        )
