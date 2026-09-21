"""
Clinical Data Models and Schemas for ClinicWorks / Vitals Platform.
Aligned with ClinicWorks Azure Architecture & Quality Measure Specifications.

Supported Measures:
- Blood Pressure (BP): format "138/88"
- HbA1c (A1C): format "7.4%" or "5.8 (Prediabetes)" / "6.5 (Diabetes)"

Outcomes:
- Success: Document classified and measure extracted.
- Needs Review: Document understood, but clinical value could not be reliably identified.
- Failed: Technical error prevented processing.
"""

from enum import Enum
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone

try:
    from pydantic import BaseModel, Field
except ImportError:
    # Standard library fallback when pydantic is not yet installed
    class BaseModel:
        def __init__(self, **kwargs):
            # Collect defaults from class annotations and class attributes
            for cls in reversed(self.__class__.__mro__):
                for k in getattr(cls, '__annotations__', {}):
                    if hasattr(cls, k):
                        val = getattr(cls, k)
                        setattr(self, k, val() if callable(val) and not isinstance(val, type) else val)
            for k, v in kwargs.items():
                setattr(self, k, v)

        def model_dump(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

        def dict(self) -> Dict[str, Any]:
            return self.model_dump()

    def Field(default=None, default_factory=None, **kwargs):
        if default_factory is not None:
            return default_factory
        return default


class MeasureType(str, Enum):
    """Supported Clinical Quality Measures."""
    BP = "BP"
    A1C = "A1C"
    UNKNOWN = "UNKNOWN"


class DocumentType(str, Enum):
    """Clinical classification of the uploaded document."""
    DISCHARGE_SUMMARY = "discharge_summary"
    OUTPATIENT_NOTE = "outpatient_note"
    LAB_REPORT = "lab_report"
    EMERGENCY_NOTE = "emergency_note"
    NON_CLINICAL = "non_clinical"
    UNKNOWN = "unknown"


class ProcessingOutcome(str, Enum):
    """The 3 Official Assignment Processing Outcomes."""
    SUCCESS = "Success"
    NEEDS_REVIEW = "Needs Review"
    FAILED = "Failed"


class ProcessingStatus(str, Enum):
    """Lifecycle status of a document in the processing pipeline."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    VALIDATION_FAILED = "validation_failed"
    ERROR = "error"
    RETRY_PENDING = "retry_pending"


class ValidationSeverity(str, Enum):
    """Severity of a business rule evaluation."""
    PASSED = "passed"
    WARNING = "warning"
    CRITICAL_ERROR = "critical_error"


class BPReadingCandidate(BaseModel):
    """Candidate Blood Pressure measurement extracted from document text or image."""
    systolic: Optional[int] = Field(default=None, description="Systolic value (upper number)")
    diastolic: Optional[int] = Field(default=None, description="Diastolic value (lower number)")
    date: Optional[str] = Field(default=None, description="Date of reading if stated (YYYY-MM-DD or as written)")
    is_goal_or_historical: bool = Field(default=False, description="True if labeled as goal, target, previous, or past reading")
    raw_snippet: Optional[str] = Field(default=None, description="Excerpt from text")


class A1CReadingCandidate(BaseModel):
    """Candidate HbA1c measurement extracted from document text or image."""
    value: Optional[float] = Field(default=None, description="Numeric HbA1c value (e.g. 5.8)")
    date: Optional[str] = Field(default=None, description="Date of specimen collection if stated")
    is_goal_or_historical: bool = Field(default=False, description="True if labeled as target, goal, reference range, or historical example")
    raw_snippet: Optional[str] = Field(default=None, description="Excerpt from text")


class BloodPressure(BaseModel):
    """Extracted Blood Pressure measurement for backward compatibility."""
    systolic: Optional[int] = Field(default=None)
    diastolic: Optional[int] = Field(default=None)
    unit: str = Field(default="mmHg")
    raw_snippet: Optional[str] = Field(default=None)
    measured_at: Optional[str] = Field(default=None)


class HbA1c(BaseModel):
    """Extracted Glycated Hemoglobin (HbA1c) measurement for backward compatibility."""
    value: Optional[float] = Field(default=None)
    unit: str = Field(default="%")
    raw_snippet: Optional[str] = Field(default=None)
    collection_date: Optional[str] = Field(default=None)


class ClinicalExtractionResult(BaseModel):
    """Raw extraction returned by Azure OpenAI model."""
    patient_id: Optional[str] = Field(default=None, description="Patient identifier")
    patient_age: Optional[int] = Field(default=None, description="Patient age if mentioned in years")
    document_type: MeasureType = Field(default=MeasureType.UNKNOWN, description="Classified measure type (BP, A1C, UNKNOWN)")
    is_clinical_document: bool = Field(default=True, description="False if invoice or non-medical")
    
    # Lists of candidate readings
    bp_candidates: List[BPReadingCandidate] = Field(default_factory=list)
    a1c_candidates: List[A1CReadingCandidate] = Field(default_factory=list)
    
    model_extraction_quality: float = Field(default=1.0, description="Model self-confidence score (0.0 to 1.0)")
    raw_observations: Optional[str] = Field(default=None, description="Contextual clinical notes")

    # Backward compatibility properties
    @property
    def blood_pressure(self) -> Optional[BloodPressure]:
        if self.bp_candidates and self.bp_candidates[0].systolic is not None:
            return BloodPressure(
                systolic=self.bp_candidates[0].systolic,
                diastolic=self.bp_candidates[0].diastolic,
                raw_snippet=self.bp_candidates[0].raw_snippet,
                measured_at=self.bp_candidates[0].date
            )
        return None

    @property
    def hba1c(self) -> Optional[HbA1c]:
        if self.a1c_candidates and self.a1c_candidates[0].value is not None:
            return HbA1c(
                value=self.a1c_candidates[0].value,
                raw_snippet=self.a1c_candidates[0].raw_snippet,
                collection_date=self.a1c_candidates[0].date
            )
        return None


class RuleEvaluation(BaseModel):
    """Result of an individual business rule evaluation."""
    rule_id: str = Field(default="")
    rule_name: str = Field(default="")
    severity: ValidationSeverity = Field(default=ValidationSeverity.PASSED)
    passed: bool = Field(default=True)
    message: str = Field(default="")
    clinical_category: Optional[str] = Field(default=None)


class ValidationSummary(BaseModel):
    """Summary of business rules evaluation."""
    overall_valid: bool = Field(default=True)
    requires_human_review: bool = Field(default=False)
    requires_retry: bool = Field(default=False)
    evaluations: List[RuleEvaluation] = Field(default_factory=list)
    summary_message: str = Field(default="")
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FinalProcessedDocument(BaseModel):
    """
    Final verified result persisted in PostgreSQL and displayed in the Web App table.
    Fields match the Azure Assignment specification:
    - Document Name
    - Document Type (BP, A1C)
    - Measure ("138/88", "5.8 (Prediabetes)", "6.5 (Diabetes)")
    - Associated Date
    - Status ("Success", "Needs Review", "Failed")
    - Status Reason
    - Action (Retry mechanism)
    """
    document_name: str = Field(default="")
    document_type: MeasureType = Field(default=MeasureType.UNKNOWN)
    measure: Optional[str] = Field(default=None)
    associated_date: Optional[str] = Field(default=None)
    status: ProcessingOutcome = Field(default=ProcessingOutcome.SUCCESS)
    confidence_score: float = Field(default=0.0)
    status_reason: Optional[str] = Field(default=None)
    patient_id: Optional[str] = Field(default=None)
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
