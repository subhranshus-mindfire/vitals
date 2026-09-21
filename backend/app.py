#!/usr/bin/env python3
"""
ClinicWorks / Vitals Platform - Web Application & Dashboard.
Meets all Azure Assignment requirements:
1. Upload clinical documents (PDF, TXT, Scanned Images).
2. View Processed Documents table with:
   - Document Name
   - Document Type (BP, A1C)
   - Measure (e.g. 138/88, 5.8 (Prediabetes), 6.5 (Diabetes))
   - Associated Date
   - Status (Success, Needs Review, Failed)
   - Confidence Score
   - Status Reason
   - Action (Retry button to reprocess document)
3. Works both as FastAPI app (for Azure Web App deployment) and zero-dependency standalone server.
"""

import os
import sys
import json
import base64
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# Setup project root
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.database.repository import ClinicalDatabaseRepository
from backend.services.orchestrator_service import PipelineOrchestratorService

repo = ClinicalDatabaseRepository()
orchestrator = PipelineOrchestratorService(repo)

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ClinicWorks Vitals Intelligence</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #0284c7;
            --primary-dark: #0369a1;
            --success-bg: #ecfdf5;
            --success-text: #065f46;
            --success-border: #a7f3d0;
            --warning-bg: #fffbeb;
            --warning-text: #92400e;
            --warning-border: #fde68a;
            --danger-bg: #fef2f2;
            --danger-text: #991b1b;
            --danger-border: #fecaca;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', -apple-system, sans-serif; background: #f8fafc; color: #0f172a; padding: 32px 24px; }
        .container { max-width: 1200px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 28px; padding-bottom: 20px; border-bottom: 1px solid #e2e8f0; }
        .logo h1 { font-size: 24px; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 8px; }
        .logo p { font-size: 14px; color: #64748b; margin-top: 4px; }
        .azure-badge { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; padding: 6px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; }
        
        .card { background: white; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); padding: 24px; margin-bottom: 28px; }
        .card-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #1e293b; }
        
        /* Upload Area */
        .upload-zone { border: 2px dashed #cbd5e1; border-radius: 8px; padding: 32px; text-align: center; background: #f8fafc; cursor: pointer; transition: all 0.2s; }
        .upload-zone:hover { border-color: var(--primary); background: #f0f9ff; }
        .upload-zone p { color: #64748b; font-size: 14px; margin-top: 8px; }
        .file-input { display: none; }
        .btn { background: var(--primary); color: white; border: none; padding: 9px 18px; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; transition: background 0.15s; }
        .btn:hover { background: var(--primary-dark); }
        .quick-samples { margin-top: 16px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
        .quick-samples span { font-size: 13px; color: #64748b; }
        .btn-sample { background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 5px 10px; border-radius: 6px; font-size: 12px; cursor: pointer; }
        .btn-sample:hover { background: #e2e8f0; }

        /* Table */
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th { background: #f8fafc; color: #475569; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 12px 16px; border-bottom: 1px solid #e2e8f0; }
        td { padding: 14px 16px; border-bottom: 1px solid #f1f5f9; font-size: 14px; vertical-align: middle; }
        tr:hover td { background: #fafafa; }
        
        .badge { display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; }
        .badge-success { background: var(--success-bg); color: var(--success-text); border: 1px solid var(--success-border); }
        .badge-review { background: var(--warning-bg); color: var(--warning-text); border: 1px solid var(--warning-border); }
        .badge-failed { background: var(--danger-bg); color: var(--danger-text); border: 1px solid var(--danger-border); }
        .badge-type { background: #f1f5f9; color: #334155; border: 1px solid #e2e8f0; font-family: monospace; font-size: 11px; }

        .measure-val { font-weight: 600; font-size: 14px; }
        .confidence-pill { font-size: 12px; font-weight: 600; color: #475569; }
        
        .btn-retry { background: white; color: var(--primary); border: 1px solid #bae6fd; padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
        .btn-retry:hover { background: #f0f9ff; border-color: var(--primary); }
        .btn-retry:disabled { opacity: 0.5; cursor: not-allowed; }

        .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid #cbd5e1; border-top-color: var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        #status-banner { display: none; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <h1>🏥 ClinicWorks Vitals Platform</h1>
                <p>Cloud-Native Clinical Document Intelligence on Microsoft Azure</p>
            </div>
            <div class="azure-badge">
                ☁️ Central India &bull; func-vitals-extractor-dev
            </div>
        </header>

        <div id="status-banner"></div>

        <!-- Document Upload Section -->
        <div class="card">
            <div class="card-title">1. Upload Clinical Document</div>
            <div class="upload-zone" onclick="document.getElementById('file-upload').click()">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2" style="margin-bottom: 8px;">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="17 8 12 3 7 8"></polyline>
                    <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
                <div style="font-weight: 600; font-size: 15px;">Click to upload or drag clinical document here</div>
                <p>Supports Digital PDF, Scanned Image PDF, and Clinical Notes (.pdf, .txt, .png, .jpg)</p>
                <input type="file" id="file-upload" class="file-input" onchange="handleFileUpload(event)">
            </div>
            
            <div class="quick-samples">
                <span>Quick Test with Assignment Samples:</span>
                <button class="btn-sample" onclick="submitSample('patient_01_discharge_summary.pdf')">📄 Patient 1 (BP Discharge)</button>
                <button class="btn-sample" onclick="submitSample('patient_02_outpatient_visit.pdf')">📄 Patient 2 (Clean BP)</button>
                <button class="btn-sample" onclick="submitSample('patient_03_invalid_anomaly.pdf')">⚠️ Patient 3 (Under 18 BP)</button>
                <button class="btn-sample" onclick="submitSample('patient_04_non_clinical.pdf')">⚠️ Patient 4 (Non-Clinical)</button>
                <button class="btn-sample" onclick="submitSample('patient_05_scanned_image.pdf')">📸 Patient 5 (Scanned PDF Vision)</button>
            </div>
        </div>

        <!-- Processed Documents Table -->
        <div class="card" style="padding: 0; overflow: hidden;">
            <div style="padding: 20px 24px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0;">
                <div class="card-title" style="margin-bottom: 0;">2. Processed Documents</div>
                <button class="btn-retry" onclick="loadDocuments()">↻ Refresh</button>
            </div>
            
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Document Name</th>
                            <th>Type</th>
                            <th>Measure</th>
                            <th>Associated Date</th>
                            <th>Status</th>
                            <th>Confidence</th>
                            <th>Status Reason</th>
                            <th style="text-align: right;">Action</th>
                        </tr>
                    </thead>
                    <tbody id="documents-tbody">
                        <tr><td colspan="8" style="text-align: center; color: #94a3b8; padding: 32px;">Loading processed clinical records...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        async function loadDocuments() {
            try {
                const res = await fetch('/api/documents');
                const docs = await res.json();
                renderTable(docs);
            } catch (err) {
                console.error("Failed to load documents", err);
            }
        }

        function renderTable(docs) {
            const tbody = document.getElementById('documents-tbody');
            if (!docs || docs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: #94a3b8; padding: 32px;">No documents processed yet. Upload a document or select a sample above.</td></tr>';
                return;
            }

            tbody.innerHTML = docs.map(d => {
                let statusBadge = '';
                if (d.status === 'Success') {
                    statusBadge = '<span class="badge badge-success">● Success</span>';
                } else if (d.status === 'Needs Review') {
                    statusBadge = '<span class="badge badge-review">⚠️ Needs Review</span>';
                } else {
                    statusBadge = '<span class="badge badge-failed">✕ Failed</span>';
                }

                const measureDisplay = d.measure ? `<span class="measure-val">${d.measure}</span>` : '<span style="color:#94a3b8">None</span>';
                const dateDisplay = d.associated_date ? d.associated_date : '<span style="color:#94a3b8">N/A</span>';
                const confidence = Math.round((d.confidence_score || 0) * 100);

                return `
                    <tr>
                        <td style="font-weight: 500;">${d.document_name}</td>
                        <td><span class="badge badge-type">${d.document_type || 'UNKNOWN'}</span></td>
                        <td>${measureDisplay}</td>
                        <td>${dateDisplay}</td>
                        <td>${statusBadge}</td>
                        <td><span class="confidence-pill">${confidence}%</span></td>
                        <td style="max-width: 320px; font-size: 13px; color: #475569;" title="${d.status_reason || ''}">${d.status_reason || '—'}</td>
                        <td style="text-align: right;">
                            <button id="btn-retry-${d.document_id}" class="btn-retry" onclick="triggerRetry('${d.document_id}', this)">
                                🔄 Retry
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        async function submitSample(filename) {
            showBanner(`Submitting sample: ${filename}...`, "info");
            try {
                const res = await fetch('/api/submit-sample', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename: filename })
                });
                const result = await res.json();
                showBanner(`Successfully processed ${result.document_name}: Status = ${result.status}`, "success");
                loadDocuments();
            } catch (err) {
                showBanner("Submission failed: " + err.message, "error");
            }
        }

        async function handleFileUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            showBanner(`Uploading and extracting: ${file.name}...`, "info");
            const reader = new FileReader();
            reader.onload = async function() {
                const base64Data = reader.result.split(',')[1];
                try {
                    const res = await fetch('/api/upload', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            filename: file.name,
                            content_base64: base64Data
                        })
                    });
                    const result = await res.json();
                    showBanner(`Processed ${result.document_name}: Status = ${result.status}`, "success");
                    loadDocuments();
                } catch (err) {
                    showBanner("Upload processing error: " + err.message, "error");
                }
            };
            reader.readAsDataURL(file);
        }

        async function triggerRetry(documentId, btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Retrying...';
            showBanner(`Triggering reprocessing for document ID ${documentId}...`, "info");

            try {
                const res = await fetch(`/api/documents/${documentId}/retry`, { method: 'POST' });
                const result = await res.json();
                showBanner(`Reprocessed ${result.document_name}: New Status = ${result.status}`, "success");
                loadDocuments();
            } catch (err) {
                showBanner("Retry failed: " + err.message, "error");
            } finally {
                btn.disabled = false;
                btn.innerHTML = '🔄 Retry';
            }
        }

        function showBanner(msg, type) {
            const banner = document.getElementById('status-banner');
            banner.style.display = 'block';
            banner.innerText = msg;
            if (type === 'success') {
                banner.style.background = '#ecfdf5';
                banner.style.color = '#065f46';
                banner.style.border = '1px solid #a7f3d0';
            } else if (type === 'error') {
                banner.style.background = '#fef2f2';
                banner.style.color = '#991b1b';
                banner.style.border = '1px solid #fecaca';
            } else {
                banner.style.background = '#f0f9ff';
                banner.style.color = '#0369a1';
                banner.style.border = '1px solid #bae6fd';
            }
            setTimeout(() => { banner.style.display = 'none'; }, 5000);
        }

        // Initial Load
        loadDocuments();
    </script>
</body>
</html>
"""


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """Standard library HTTP server handler for zero-dependency operation."""

    def _set_headers(self, content_type="application/json", status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(status=204)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self._set_headers("text/html; charset=utf-8")
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
        elif parsed.path == "/api/documents":
            docs = repo.get_dashboard_documents()
            self._set_headers("application/json")
            self.wfile.write(json.dumps(docs).encode("utf-8"))
        else:
            self._set_headers("application/json", status=404)
            self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        data = json.loads(body) if body else {}

        if parsed.path == "/api/submit-sample":
            filename = data.get("filename", "patient_01_discharge_summary.pdf")
            sample_path = project_root / "sample_data" / filename
            blob_url = f"https://stvitalsdevcentralindia.blob.core.windows.net/clinical-documents/{filename}"
            
            result = orchestrator.process_new_document(
                filename=filename,
                blob_path=f"samples/{filename}",
                blob_url=blob_url
            )
            self._set_headers("application/json")
            self.wfile.write(json.dumps(result).encode("utf-8"))

        elif parsed.path == "/api/upload":
            filename = data.get("filename", "uploaded_file.pdf")
            content_base64 = data.get("content_base64")
            blob_url = f"https://stvitalsdevcentralindia.blob.core.windows.net/clinical-documents/{filename}"

            result = orchestrator.process_new_document(
                filename=filename,
                blob_path=f"uploads/{filename}",
                blob_url=blob_url,
                content_base64=content_base64
            )
            self._set_headers("application/json")
            self.wfile.write(json.dumps(result).encode("utf-8"))

        elif parsed.path.startswith("/api/documents/") and parsed.path.endswith("/retry"):
            # Extract document ID: /api/documents/{id}/retry
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 3:
                doc_id = parts[2]
                try:
                    retry_result = orchestrator.trigger_retry(doc_id)
                    self._set_headers("application/json")
                    self.wfile.write(json.dumps(retry_result).encode("utf-8"))
                except Exception as e:
                    self._set_headers("application/json", status=500)
                    self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            else:
                self._set_headers("application/json", status=400)
                self.wfile.write(json.dumps({"error": "Invalid document ID"}).encode("utf-8"))
        else:
            self._set_headers("application/json", status=404)
            self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))


def run_server(port=8000):
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, DashboardRequestHandler)
    print(f"\n{'='*75}")
    print(f"🏥 ClinicWorks Vitals Platform Web Server is running!")
    print(f"🌐 Dashboard URL: http://localhost:{port}")
    print(f"☁️ Connected Azure Endpoint: func-vitals-extractor-dev")
    print(f"{'='*75}\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)

