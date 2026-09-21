"""
Clinical Business Rules Engine for ClinicWorks Platform.

Implements all assignment business rules:
1. BP Rules:
   - Patient under age 18: Do not return BP result (Status: Needs Review).
   - Filter out goal BP, target BP, past BP, previous BP.
   - Multiple BP readings: Return most recent clearly dated result.
   - Undated/unresolvable multiple readings: Return lowest BP based on (systolic + diastolic).
   - Valid BP must contain both systolic and diastolic values.
2. HbA1c Rules:
   - Filter out reference ranges, goals, targets, historical examples.
   - Multiple HbA1c readings: Return lowest value.
   - If HbA1c > 5.7: Return classification "Prediabetes" (e.g. "5.8 (Prediabetes)").
   - If HbA1c > 5.9: Return classification "Diabetes" (e.g. "6.5 (Diabetes)").
   - If HbA1c <= 5.7: Return normal format (e.g. "5.4%").
3. Confidence Scoring:
   - Evaluates extraction quality, presence of required fields, and rule adherence (0.00 to 1.00).
4. Three Official Processing Outcomes:
   - "Success", "Needs Review", "Failed".
"""

from typing import List, Optional
from datetime import datetime
from backend.models.clinical import (
    ClinicalExtractionResult,
    FinalProcessedDocument,
    ValidationSummary,
    RuleEvaluation,
    ValidationSeverity,
    MeasureType,
    ProcessingOutcome,
    BPReadingCandidate,
    A1CReadingCandidate,
)


class ClinicWorksRulesEngine:
    """Executes centralized clinical business rules on extracted data."""

    # Physiological plausibility boundaries
    MIN_SYSTOLIC = 50
    MAX_SYSTOLIC = 280
    MIN_DIASTOLIC = 30
    MAX_DIASTOLIC = 180

    MIN_HBA1C = 3.0
    MAX_HBA1C = 20.0

    def process(self, extraction: ClinicalExtractionResult, document_name: str) -> FinalProcessedDocument:
        """
        Applies all clinical business rules and produces the final verified document
        to be stored in PostgreSQL and displayed in the Web App dashboard.
        """
        # 1. Non-clinical or unidentifiable document
        if not extraction.is_clinical_document:
            return FinalProcessedDocument(
                document_name=document_name,
                document_type=MeasureType.UNKNOWN,
                measure=None,
                associated_date=None,
                status=ProcessingOutcome.NEEDS_REVIEW,
                confidence_score=0.10,
                status_reason="Document identified as non-clinical (invoice, receipt, or administrative memo).",
                patient_id=extraction.patient_id,
            )

        # Determine target measure from classification and candidates
        target_type = extraction.document_type
        if target_type == MeasureType.UNKNOWN:
            if extraction.bp_candidates and not extraction.a1c_candidates:
                target_type = MeasureType.BP
            elif extraction.a1c_candidates and not extraction.bp_candidates:
                target_type = MeasureType.A1C
            elif extraction.bp_candidates and extraction.a1c_candidates:
                target_type = MeasureType.BP

        if target_type == MeasureType.BP:
            return self._process_blood_pressure(extraction, document_name)
        elif target_type == MeasureType.A1C:
            return self._process_hba1c(extraction, document_name)
        else:
            return FinalProcessedDocument(
                document_name=document_name,
                document_type=MeasureType.UNKNOWN,
                measure=None,
                associated_date=None,
                status=ProcessingOutcome.NEEDS_REVIEW,
                confidence_score=0.20,
                status_reason="Unable to identify supported quality measure (neither Blood Pressure nor HbA1c detected).",
                patient_id=extraction.patient_id,
            )

    def _process_blood_pressure(self, extraction: ClinicalExtractionResult, document_name: str) -> FinalProcessedDocument:
        """Evaluates Blood Pressure against all clinical guidelines."""
        # Rule 1: Patient under age 18 -> Do not return BP result (Needs Review)
        if extraction.patient_age is not None and extraction.patient_age < 18:
            return FinalProcessedDocument(
                document_name=document_name,
                document_type=MeasureType.BP,
                measure=None,
                associated_date=None,
                status=ProcessingOutcome.NEEDS_REVIEW,
                confidence_score=0.85,
                status_reason=f"Patient is under age 18 (age {extraction.patient_age}). BP result withheld per clinical guidelines.",
                patient_id=extraction.patient_id,
            )

        # Rule 4: Filter out goal, target, or past readings
        active_candidates = [
            c for c in extraction.bp_candidates
            if not getattr(c, 'is_goal_or_historical', False)
        ]

        # Rule 3: Valid entry must contain both systolic and diastolic values
        valid_candidates = []
        for c in active_candidates:
            if c.systolic is not None and c.diastolic is not None:
                # Plausibility check
                if (self.MIN_SYSTOLIC <= c.systolic <= self.MAX_SYSTOLIC and
                    self.MIN_DIASTOLIC <= c.diastolic <= self.MAX_DIASTOLIC and
                    c.systolic > c.diastolic):
                    valid_candidates.append(c)

        if not valid_candidates:
            has_goal = any(getattr(c, 'is_goal_or_historical', False) for c in extraction.bp_candidates)
            reason = "Document contains only goal/target/past BP readings; no active reading found." if has_goal else "No valid blood pressure reading with both systolic and diastolic values found."
            return FinalProcessedDocument(
                document_name=document_name,
                document_type=MeasureType.BP,
                measure=None,
                associated_date=None,
                status=ProcessingOutcome.NEEDS_REVIEW,
                confidence_score=0.30,
                status_reason=reason,
                patient_id=extraction.patient_id,
            )

        # Rule 2: Multiple valid readings
        selected_candidate: BPReadingCandidate
        selection_reason: str

        if len(valid_candidates) == 1:
            selected_candidate = valid_candidates[0]
            selection_reason = "Single valid Blood Pressure reading identified."
        else:
            # Check for clearly dated readings
            dated_candidates = [c for c in valid_candidates if c.date]
            if dated_candidates:
                # Attempt sorting by date descending
                try:
                    dated_candidates.sort(
                        key=lambda x: datetime.fromisoformat(x.date.replace("Z", "+00:00")),
                        reverse=True
                    )
                    selected_candidate = dated_candidates[0]
                    selection_reason = f"Selected most recent reading ({selected_candidate.date}) from {len(valid_candidates)} candidates."
                except Exception:
                    # Fallback to string sort or lowest sum
                    dated_candidates.sort(key=lambda x: str(x.date), reverse=True)
                    selected_candidate = dated_candidates[0]
                    selection_reason = f"Selected latest dated reading ({selected_candidate.date})."
            else:
                # Undated multiple readings: Return lowest based on sum of (systolic + diastolic)
                valid_candidates.sort(key=lambda x: (x.systolic + x.diastolic))
                selected_candidate = valid_candidates[0]
                selection_reason = f"Selected lowest BP ({selected_candidate.systolic}/{selected_candidate.diastolic}) by sum of values among {len(valid_candidates)} undated readings."

        # Compute confidence score
        confidence = self._calculate_confidence(
            extraction_quality=extraction.model_extraction_quality,
            has_patient_id=bool(extraction.patient_id),
            has_date=bool(selected_candidate.date),
            is_single=(len(valid_candidates) == 1),
            all_valid=True
        )

        return FinalProcessedDocument(
            document_name=document_name,
            document_type=MeasureType.BP,
            measure=f"{selected_candidate.systolic}/{selected_candidate.diastolic}",
            associated_date=selected_candidate.date,
            status=ProcessingOutcome.SUCCESS,
            confidence_score=confidence,
            status_reason=selection_reason,
            patient_id=extraction.patient_id,
        )

    def _process_hba1c(self, extraction: ClinicalExtractionResult, document_name: str) -> FinalProcessedDocument:
        """Evaluates HbA1c against clinical guidelines."""
        # Rule 2: Filter out reference ranges, targets, or historical examples
        active_candidates = [
            c for c in extraction.a1c_candidates
            if not getattr(c, 'is_goal_or_historical', False)
        ]

        # Plausibility check
        valid_candidates = [
            c for c in active_candidates
            if c.value is not None and self.MIN_HBA1C <= c.value <= self.MAX_HBA1C
        ]

        if not valid_candidates:
            has_ref = any(getattr(c, 'is_goal_or_historical', False) for c in extraction.a1c_candidates)
            reason = "Document contains only reference ranges or target goals; no active lab result found." if has_ref else "No valid HbA1c lab result found."
            return FinalProcessedDocument(
                document_name=document_name,
                document_type=MeasureType.A1C,
                measure=None,
                associated_date=None,
                status=ProcessingOutcome.NEEDS_REVIEW,
                confidence_score=0.30,
                status_reason=reason,
                patient_id=extraction.patient_id,
            )

        # Rule 1: Multiple readings -> Always return lowest value
        valid_candidates.sort(key=lambda x: x.value)
        selected_candidate: A1CReadingCandidate = valid_candidates[0]

        val = selected_candidate.value
        # Rule 3: Include classification based on value
        # > 5.9: Diabetes (example output: 6.5 (Diabetes))
        # > 5.7: Prediabetes (example output: 5.8 (Prediabetes))
        if val > 5.9:
            formatted_measure = f"{val} (Diabetes)"
        elif val > 5.7:
            formatted_measure = f"{val} (Prediabetes)"
        else:
            formatted_measure = f"{val}%"

        selection_reason = (
            f"Selected lowest HbA1c ({val}) from {len(valid_candidates)} candidates."
            if len(valid_candidates) > 1
            else f"Extracted valid HbA1c value ({val})."
        )

        confidence = self._calculate_confidence(
            extraction_quality=extraction.model_extraction_quality,
            has_patient_id=bool(extraction.patient_id),
            has_date=bool(selected_candidate.date),
            is_single=(len(valid_candidates) == 1),
            all_valid=True
        )

        return FinalProcessedDocument(
            document_name=document_name,
            document_type=MeasureType.A1C,
            measure=formatted_measure,
            associated_date=selected_candidate.date,
            status=ProcessingOutcome.SUCCESS,
            confidence_score=confidence,
            status_reason=selection_reason,
            patient_id=extraction.patient_id,
        )

    def _calculate_confidence(
        self,
        extraction_quality: float,
        has_patient_id: bool,
        has_date: bool,
        is_single: bool,
        all_valid: bool
    ) -> float:
        """Calculates confidence score between 0.00 and 1.00 based on extraction quality and completeness."""
        score = float(extraction_quality) * 0.70
        if has_patient_id:
            score += 0.10
        if has_date:
            score += 0.10
        if is_single:
            score += 0.05
        if all_valid:
            score += 0.05
        return round(min(max(score, 0.0), 1.0), 2)

    def evaluate(self, extraction: ClinicalExtractionResult) -> ValidationSummary:
        """Evaluation method for audit logging and compatibility."""
        doc = self.process(extraction, "document")
        is_success = (doc.status == ProcessingOutcome.SUCCESS)
        evals = [
            RuleEvaluation(
                rule_id="EVAL-01",
                rule_name=f"{doc.document_type.value} Rule Check",
                severity=ValidationSeverity.PASSED if is_success else ValidationSeverity.WARNING,
                passed=is_success,
                message=doc.status_reason or "Evaluation completed",
                clinical_category=doc.measure
            )
        ]
        return ValidationSummary(
            overall_valid=is_success,
            requires_human_review=(doc.status == ProcessingOutcome.NEEDS_REVIEW),
            requires_retry=(doc.status == ProcessingOutcome.FAILED),
            evaluations=evals,
            summary_message=doc.status_reason or "Completed"
        )


# Backward-compatible alias
ClinicalBusinessRulesEngine = ClinicWorksRulesEngine
