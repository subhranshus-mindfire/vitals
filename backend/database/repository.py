"""
Database Repository for ClinicWorks / Vitals Platform.
Supports:
1. Azure Database for PostgreSQL (Flexible Server) when DB_HOST / connection configured.
2. SQLite (vitals.db) automatic local fallback for zero-friction local development.
Persists:
- documents
- vital_metrics
- validation_logs
- retry_history
"""

import os
import uuid
import json
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
LOCAL_DB_PATH = project_root / "vitals.db"


class ClinicalDatabaseRepository:
    """Manages persistence for documents, vital metrics, and retry history."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or LOCAL_DB_PATH
        self._init_sqlite_schema()

    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite_schema(self):
        """Creates SQLite tables matching the PostgreSQL schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                blob_path TEXT NOT NULL UNIQUE,
                blob_url TEXT NOT NULL,
                patient_id TEXT,
                document_type TEXT DEFAULT 'UNKNOWN',
                status TEXT NOT NULL DEFAULT 'uploaded',
                retry_count INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 3,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS vital_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                patient_id TEXT,
                document_type TEXT,
                measure TEXT,
                associated_date TEXT,
                status TEXT,
                confidence_score REAL DEFAULT 1.0,
                status_reason TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS retry_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                attempt_number INTEGER NOT NULL,
                triggered_by TEXT NOT NULL,
                previous_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL
            );
            """)
            conn.commit()

    def create_document(self, filename: str, blob_path: str, blob_url: str, patient_id: Optional[str] = None) -> str:
        """Registers an uploaded document."""
        doc_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO documents (id, filename, blob_path, blob_url, patient_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'uploaded', ?, ?)
            """, (doc_id, filename, blob_path, blob_url, patient_id, now, now))
            conn.commit()
        return doc_id

    def update_document_processing_result(
        self,
        document_id: str,
        document_type: str,
        measure: Optional[str],
        associated_date: Optional[str],
        status: str,
        confidence_score: float,
        status_reason: Optional[str],
        patient_id: Optional[str] = None
    ):
        """Updates document record and stores the extracted vital metric."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Update document state
            cursor.execute("""
                UPDATE documents
                SET document_type = ?,
                    status = ?,
                    patient_id = COALESCE(?, patient_id),
                    updated_at = ?
                WHERE id = ?
            """, (document_type, status, patient_id, now, document_id))

            # Record in vital_metrics table
            cursor.execute("""
                INSERT INTO vital_metrics (
                    document_id, patient_id, document_type, measure, associated_date,
                    status, confidence_score, status_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id, patient_id, document_type, measure, associated_date,
                status, confidence_score, status_reason, now
            ))
            conn.commit()

    def record_retry(self, document_id: str, triggered_by: str, reason: str = "Clinician manual reprocess"):
        """Records a retry event in retry_history and increments document retry count."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, retry_count FROM documents WHERE id = ?", (document_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Document with ID {document_id} not found.")

            prev_status = row["status"]
            new_retry_count = row["retry_count"] + 1

            # Update document to processing / retry_pending
            cursor.execute("""
                UPDATE documents
                SET status = 'processing',
                    retry_count = ?,
                    updated_at = ?
                WHERE id = ?
            """, (new_retry_count, now, document_id))

            # Insert retry history audit entry
            cursor.execute("""
                INSERT INTO retry_history (
                    document_id, attempt_number, triggered_by, previous_status,
                    new_status, reason, created_at
                ) VALUES (?, ?, ?, ?, 'processing', ?, ?)
            """, (document_id, new_retry_count, triggered_by, prev_status, reason, now))

            conn.commit()
            return new_retry_count

    def get_dashboard_documents(self) -> List[Dict[str, Any]]:
        """
        Retrieves processed documents formatted for the Web Dashboard table:
        - Document Name
        - Document Type
        - Measure
        - Associated Date
        - Status (Success, Needs Review, Failed)
        - Confidence Score
        - Status Reason
        - Retry Count
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    d.id AS document_id,
                    d.filename AS document_name,
                    COALESCE(m.document_type, d.document_type) AS document_type,
                    m.measure,
                    m.associated_date,
                    COALESCE(m.status, d.status) AS status,
                    COALESCE(m.confidence_score, 0.0) AS confidence_score,
                    COALESCE(m.status_reason, d.error_message) AS status_reason,
                    d.retry_count,
                    d.updated_at
                FROM documents d
                LEFT JOIN (
                    SELECT * FROM vital_metrics
                    WHERE id IN (SELECT MAX(id) FROM vital_metrics GROUP BY document_id)
                ) m ON d.id = m.document_id
                ORDER BY d.updated_at DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single document by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

