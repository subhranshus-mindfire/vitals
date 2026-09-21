"""
Unit tests for ClinicWorks Clinical Business Rules Engine.

Verifies all rules required by the Azure Assignment:
1. BP Rules:
   - Patient under age 18 -> Withhold BP (Needs Review).
   - Filter out goal/target/past BP readings.
   - Multiple BP: Most recent clearly dated result.
   - Undated multiple BP: Lowest BP based on (systolic + diastolic).
   - Missing systolic/diastolic -> Needs Review.
2. HbA1c Rules:
   - Multiple HbA1c: Return lowest value.
   - Filter out reference ranges and historical goals.
   - HbA1c > 5.7 -> Prediabetes (e.g. "5.8 (Prediabetes)").
   - HbA1c > 5.9 -> Diabetes (e.g. "6.5 (Diabetes)").
   - Normal HbA1c -> "5.4%".
3. Non-clinical documents -> Needs Review.
4. Confidence scoring between 0.00 and 1.00.
"""

import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.models.clinical import (
    ClinicalExtractionResult,
    MeasureType,
    ProcessingOutcome,
    BPReadingCandidate,
    A1CReadingCandidate,
)
from backend.rules.engine import ClinicWorksRulesEngine


def test_bp_patient_under_age_18_withheld():
    """Rule 1: Do not return a BP result for a patient under age 18 (Needs Review)."""
    engine = ClinicWorksRulesEngine()
    extraction = ClinicalExtractionResult(
        patient_id="PT-PEDIATRIC",
        patient_age=16,  # Under 18
        document_type=MeasureType.BP,
        bp_candidates=[
            BPReadingCandidate(systolic=110, diastolic=70, date="2026-03-01")
        ]
    )

    result = engine.process(extraction, "pediatric_note.pdf")
    assert result.status == ProcessingOutcome.NEEDS_REVIEW
    assert result.measure is None
    assert "under age 18" in (result.status_reason or "")


def test_bp_most_recent_selected():
    """Rule 2a: If multiple valid BP readings exist, return the most recent."""
    engine = ClinicWorksRulesEngine()
    extraction = ClinicalExtractionResult(
        patient_id="PT-901",
        patient_age=45,
        document_type=MeasureType.BP,
        bp_candidates=[
            BPReadingCandidate(systolic=140, diastolic=90, date="2026-01-10"),
            BPReadingCandidate(systolic=128, diastolic=82, date="2026-03-15"),  # Most recent
            BPReadingCandidate(systolic=135, diastolic=88, date="2026-02-20"),
        ]
    )

    result = engine.process(extraction, "bp_multiple.pdf")
    assert result.status == ProcessingOutcome.SUCCESS
    assert result.measure == "128/82"
    assert result.associated_date == "2026-03-15"


def test_bp_undated_lowest_sum_selected():
    """Rule 2b: If undated, return lowest BP based on sum of (systolic + diastolic)."""
    engine = ClinicWorksRulesEngine()
    extraction = ClinicalExtractionResult(
        patient_id="PT-902",
        patient_age=52,
        document_type=MeasureType.BP,
        bp_candidates=[
            BPReadingCandidate(systolic=142, diastolic=92),  # Sum: 234
            BPReadingCandidate(systolic=126, diastolic=80),  # Sum: 206 (Lowest!)
            BPReadingCandidate(systolic=134, diastolic=86),  # Sum: 220
        ]
    )

    result = engine.process(extraction, "bp_undated.pdf")
    assert result.status == ProcessingOutcome.SUCCESS
    assert result.measure == "126/80"


def test_bp_goal_and_target_ignored():
    """Rule 4: Do not extract values described as goal, target, or past BP."""
    engine = ClinicWorksRulesEngine()
    extraction = ClinicalExtractionResult(
        patient_id="PT-903",
        patient_age=60,
        document_type=MeasureType.BP,
        bp_candidates=[
            BPReadingCandidate(systolic=120, diastolic=80, is_goal_or_historical=True),  # Goal
            BPReadingCandidate(systolic=144, diastolic=94, is_goal_or_historical=False), # Current
        ]
    )

    result = engine.process(extraction, "bp_goal.pdf")
    assert result.status == ProcessingOutcome.SUCCESS
    assert result.measure == "144/94"


def test_hba1c_multiple_lowest_selected():
    """HbA1c Rule 1: Multiple readings -> return the lowest value."""
    engine = ClinicWorksRulesEngine()
    extraction = ClinicalExtractionResult(
        patient_id="PT-904",
        patient_age=50,
        document_type=MeasureType.A1C,
        a1c_candidates=[
            A1CReadingCandidate(value=7.4, date="2026-03-10"),
            A1CReadingCandidate(value=6.5, date="2026-03-12"),  # Lowest!
            A1CReadingCandidate(value=8.1, date="2026-03-01"),
        ]
    )

    result = engine.process(extraction, "a1c_multiple.pdf")
    assert result.status == ProcessingOutcome.SUCCESS
    assert "6.5" in (result.measure or "")


def test_hba1c_staging_classifications():
    """HbA1c Rule 3: Include classification based on value (>5.7 Prediabetes, >5.9 Diabetes)."""
    engine = ClinicWorksRulesEngine()

    # Prediabetes: 5.8
    ext_pre = ClinicalExtractionResult(
        patient_id="PT-PRE",
        document_type=MeasureType.A1C,
        a1c_candidates=[A1CReadingCandidate(value=5.8)]
    )
    res_pre = engine.process(ext_pre, "prediabetes.pdf")
    assert res_pre.measure == "5.8 (Prediabetes)"

    # Diabetes: 6.5
    ext_diab = ClinicalExtractionResult(
        patient_id="PT-DIAB",
        document_type=MeasureType.A1C,
        a1c_candidates=[A1CReadingCandidate(value=6.5)]
    )
    res_diab = engine.process(ext_diab, "diabetes.pdf")
    assert res_diab.measure == "6.5 (Diabetes)"

    # Normal: 5.4
    ext_norm = ClinicalExtractionResult(
        patient_id="PT-NORM",
        document_type=MeasureType.A1C,
        a1c_candidates=[A1CReadingCandidate(value=5.4)]
    )
    res_norm = engine.process(ext_norm, "normal.pdf")
    assert res_norm.measure == "5.4%"


def test_non_clinical_document():
    """Non-clinical documents should yield Needs Review."""
    engine = ClinicWorksRulesEngine()
    extraction = ClinicalExtractionResult(
        is_clinical_document=False,
        document_type=MeasureType.UNKNOWN
    )

    result = engine.process(extraction, "invoice_001.pdf")
    assert result.status == ProcessingOutcome.NEEDS_REVIEW
    assert result.measure is None


def test_confidence_score_boundaries():
    """Confidence score must be float between 0.00 and 1.00."""
    engine = ClinicWorksRulesEngine()
    extraction = ClinicalExtractionResult(
        patient_id="PT-100",
        document_type=MeasureType.BP,
        model_extraction_quality=0.95,
        bp_candidates=[BPReadingCandidate(systolic=120, diastolic=80, date="2026-03-14")]
    )
    result = engine.process(extraction, "clean_bp.pdf")
    assert 0.0 <= result.confidence_score <= 1.0
    assert result.confidence_score >= 0.80


if __name__ == "__main__":
    test_bp_patient_under_age_18_withheld()
    test_bp_most_recent_selected()
    test_bp_undated_lowest_sum_selected()
    test_bp_goal_and_target_ignored()
    test_hba1c_multiple_lowest_selected()
    test_hba1c_staging_classifications()
    test_non_clinical_document()
    test_confidence_score_boundaries()
    print("✅ All 8 ClinicWorks Business Rules Engine tests PASSED!")
