# Azure Clinical Document Intelligence Platform
# Vitals: Azure Clinical Document Intelligence Platform

An end-to-end cloud-native solution for ingesting clinical documents, extracting critical biomarkers (**Blood Pressure** and **HbA1c**) using **Azure OpenAI**, validating clinical plausibility with a **Business Rules Engine**, persisting records in **PostgreSQL**, and orchestrating workflows and retries via **Azure Logic Apps** and **Azure Functions**.

---

## 🗺️ Learning Roadmap & Architecture

```
[Web App Upload]
       │
       ▼
[Azure Blob Storage] ◄──── (Event / Trigger)
       │
       ▼
[Azure Logic App] (Orchestrator & Retry Coordinator)
       │
       ▼
[Azure Function] (Serverless Compute)
       ├──► [Azure OpenAI] (Document Classification & Structured Extraction)
       ├──► [Business Rules Engine] (Systolic, Diastolic, HbA1c range checks)
       └──► [PostgreSQL DB] (Store documents, metrics & validation status)
       │
       ▼
[Web Dashboard] (View records, clinical alerts, trigger manual re-runs)
```

---

## 📁 Repository Structure

```
├── infra/                  # Infrastructure scripts (Azure CLI, ARM, Bicep)
├── backend/                # Core business logic
│   ├── rules/              # Clinical Business Rules Engine
│   └── models/             # Clinical data schemas (Pydantic / SQL)
├── function_app/           # Azure Functions serverless processing code
├── logic_app/              # Azure Logic App definitions (workflow.json)
├── frontend/               # Web Application (UI + retry controls)
├── sample_data/            # Sample clinical notes & lab reports for testing
└── tests/                  # Unit and integration test suites
```

---

## 🎯 Progress Tracker

- [ ] **Milestone 1**: Azure Foundation, Resource Hierarchy & Local CLI
- [ ] **Milestone 2**: Azure Blob Storage & Secure Document Ingestion
- [ ] **Milestone 3**: Database Design & Clinical Business Rules Engine
- [ ] **Milestone 4**: Azure OpenAI Structured Extraction (BP & HbA1c)
- [ ] **Milestone 5**: Azure Functions Serverless Microservice
- [ ] **Milestone 6**: Azure Logic Apps Orchestration & Retry Policies
- [ ] **Milestone 7**: Web Application Dashboard & Review Interface
- [ ] **Milestone 8**: Cloud Deployment, Security (Managed Identity) & Monitoring

