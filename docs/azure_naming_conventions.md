# Azure Resource Naming Conventions & Best Practices
# Azure Resource Naming Conventions & Best Practices: Vitals Platform

This document establishes the official naming conventions, rules, and abbreviations for all Microsoft Azure resources created in this project. All infrastructure scripts, deployment templates (Bicep/ARM/Terraform), Azure CLI commands, and agents must strictly adhere to these conventions.
This document establishes the official naming conventions, rules, and abbreviations for all Microsoft Azure resources created for the **Vitals** project. All infrastructure scripts, deployment templates (Bicep/ARM/Terraform), Azure CLI commands, and agents must strictly adhere to these conventions.

---

## 1. General Azure Naming Rules

Every resource name in Azure must comply with these foundational principles:

1. **Lowercase Letters, Numbers, and Hyphens Only**:
   - Use only `[a-z0-9-]`. No uppercase letters, spaces, or special characters.
   - *Exception*: Storage accounts and Container Registries do **NOT** support hyphens (alphanumeric only).
2. **Start and End with an Alphanumeric Character**:
   - Never start or end a name with a hyphen.
3. **No Consecutive Hyphens**:
   - Avoid double hyphens (e.g., `app--service` is invalid).
4. **Observe Maximum Lengths**:
   - Keep names under **24 characters** wherever possible to ensure compatibility across all Azure resource types (especially Storage Accounts which have a hard limit of 24 alphanumeric characters).
5. **No Personally Identifiable Information (PII)**:
   - Never embed user names, passwords, secrets, or sensitive clinical terms in resource names.
   - Never embed patient identifiers, names, secrets, or sensitive clinical data in resource names.
6. **Standard Abbreviations**:
   - Application Name: `clinext` (Clinical Document Intelligence Platform)
   - Application Name: `vitals`
   - Environments (`env`): `dev`, `test`, `qa`, `prod`
   - Regions (`reg`): `eastus`, `westeu`, `centralus`, `swedencentral`
   - Regions (`reg`): `eastus`, `westeu`, `centralus`
   - Instances: `001`, `002`

---

## 2. Resource-Specific Naming Standards

| # | Resource Type | Pattern / Format | Character Limit & Rules | Example for Our Project (`dev`, `eastus`) |
| # | Resource Type | Pattern / Format | Character Limit & Rules | Name for Our Project (`dev`, `eastus`) |
|---|---------------|------------------|-------------------------|-------------------------------------------|
| 1 | **Resource Group** | `rg-{app}-{env}-{region}` | 1–90 chars, hyphens allowed | `rg-clinext-dev-eastus` |
| 1 | **Resource Group** | `rg-{app}-{env}` or `rg-{app}-{env}-{region}` | 1–90 chars, hyphens allowed | `rg-clinical-extract-dev` |
| 2 | **Storage Account** | `st{app}{env}{region}` | **3–24 chars, lowercase + numbers ONLY (no hyphens)** | `stclinextdeveastus` (16 chars) |
| 1 | **Resource Group** | `rg-{app}-{env}-{region}` | 1–90 chars, hyphens allowed | `rg-vitals-dev-eastus` |
| 2 | **Storage Account** | `st{app}{env}{region}` | **3–24 chars, lowercase + numbers ONLY (no hyphens)** | `stvitalsdeveastus` (17 chars) |
| 3 | **Blob Container** | `{content-type}` or `{purpose}` | 3–63 chars, lowercase + hyphens | `clinical-documents`, `quarantine` |
| 4 | **Azure Functions** | `func-{app}-{function}-{env}` | 1–60 chars | `func-clinext-extractor-dev` |
| 5 | **Azure Logic Apps** | `logic-{app}-{process}-{env}` | 1–80 chars | `logic-clinext-pipeline-dev` |
| 6 | **App Service (Web App)** | `app-{app}-{env}-{region}-{instance}` | 2–60 chars | `app-clinext-dev-eastus-001` |
| 7 | **App Service Plan** | `asp-{app}-{env}-{region}` | 1–40 chars | `asp-clinext-dev-eastus` |
| 8 | **Key Vault** | `kv-{app}-{env}-{region}` | 3–24 chars | `kv-clinext-dev-eastus` (20 chars) |
| 9 | **Key Vault Secret** | `secret-{app}-{description}` | 1–127 chars, hyphens allowed | `secret-clinext-dbconnection` |
| 10 | **Azure Database (PostgreSQL / SQL)** | `sql-{app}-{env}-{region}` or `psql-{app}-{env}-{region}` | 3–63 chars | `psql-clinext-dev-eastus` |
| 11 | **Azure OpenAI Service** | `oai-{app}-{env}-{region}` | 2–64 chars | `oai-clinext-dev-eastus` |
| 12 | **User-Assigned Managed Identity** | `id-{app}-{purpose}-{env}` | 3–128 chars | `id-clinext-extractor-dev` |
| 13 | **Virtual Network (VNet)** | `vnet-{app}-{env}-{region}` | 2–64 chars | `vnet-clinext-dev-eastus` |
| 4 | **Azure Functions** | `func-{app}-{function}-{env}` | 1–60 chars | `func-vitals-extractor-dev` |
| 5 | **Azure Logic Apps** | `logic-{app}-{process}-{env}` | 1–80 chars | `logic-vitals-pipeline-dev` |
| 6 | **App Service (Web App)** | `app-{app}-{env}-{region}-{instance}` | 2–60 chars | `app-vitals-dev-eastus-001` |
| 7 | **App Service Plan** | `asp-{app}-{env}-{region}` | 1–40 chars | `asp-vitals-dev-eastus` |
| 8 | **Key Vault** | `kv-{app}-{env}-{region}` | 3–24 chars | `kv-vitals-dev-eastus` (20 chars) |
| 9 | **Key Vault Secret** | `secret-{app}-{description}` | 1–127 chars, hyphens allowed | `secret-vitals-dbconnection` |
| 10 | **Azure Database (PostgreSQL / SQL)** | `sql-{app}-{env}-{region}` or `psql-{app}-{env}-{region}` | 3–63 chars | `psql-vitals-dev-eastus` |
| 11 | **Azure OpenAI Service** | `oai-{app}-{env}-{region}` | 2–64 chars | `oai-vitals-dev-eastus` |
| 12 | **User-Assigned Managed Identity** | `id-{app}-{purpose}-{env}` | 3–128 chars | `id-vitals-extractor-dev` |
| 13 | **Virtual Network (VNet)** | `vnet-{app}-{env}-{region}` | 2–64 chars | `vnet-vitals-dev-eastus` |
| 14 | **Subnet** | `snet-{purpose}-{env}` | 1–80 chars | `snet-backend-dev` |
| 15 | **Network Security Group (NSG)** | `nsg-{associated-resource}-{env}-{region}` | 1–80 chars | `nsg-backend-dev-eastus` |
| 16 | **Container Registry (ACR)** | `cr{app}{env}` | 5–50 chars, alphanumeric only | `crclinextdev` |
| 17 | **Service Bus Namespace** | `sb-{app}-{purpose}-{env}` | 6–50 chars | `sb-clinext-events-dev` |
| 18 | **Event Hub** | `evh-{app}-{event-type}-{env}` | 1–50 chars | `evh-clinext-ingest-dev` |
| 19 | **Application Insights** | `appi-{app}-{env}-{region}` | 1–260 chars | `appi-clinext-dev-eastus` |
| 20 | **Log Analytics Workspace** | `log-{app}-{env}-{region}` | 4–63 chars | `log-clinext-dev-eastus` |
| 16 | **Container Registry (ACR)** | `cr{app}{env}` | 5–50 chars, alphanumeric only | `crvitalsdev` |
| 17 | **Service Bus Namespace** | `sb-{app}-{purpose}-{env}` | 6–50 chars | `sb-vitals-events-dev` |
| 18 | **Event Hub** | `evh-{app}-{event-type}-{env}` | 1–50 chars | `evh-vitals-ingest-dev` |
| 19 | **Application Insights** | `appi-{app}-{env}-{region}` | 1–260 chars | `appi-vitals-dev-eastus` |
| 20 | **Log Analytics Workspace** | `log-{app}-{env}-{region}` | 4–63 chars | `log-vitals-dev-eastus` |

---

## 3. Project Configuration Matrix (Clinical Intelligence Platform)
## 3. Project Configuration Matrix (Vitals Platform)

For our active project development in `eastus` on the `dev` environment:
For our active development in `eastus` on the `dev` environment:

| Role | Azure Resource Type | Standardized Project Name |
|---|---|---|
| **Solution Boundary** | Resource Group | `rg-clinext-dev-eastus` |
| **Solution Boundary** | Resource Group | `rg-clinical-extract-dev` |
| **Document Storage** | Storage Account | `stclinextdeveastus` |
| **Solution Boundary** | Resource Group | `rg-vitals-dev-eastus` |
| **Document Storage** | Storage Account | `stvitalsdeveastus` |
| **Raw Documents** | Blob Container | `clinical-documents` |
| **AI Classifier & Extractor** | Azure OpenAI Account | `oai-clinext-dev-eastus` |
| **Core Compute** | Azure Function App | `func-clinext-extractor-dev` |
| **Workflow Coordinator** | Azure Logic App | `logic-clinext-pipeline-dev` |
| **Persistent Storage** | Azure Database for PostgreSQL | `psql-clinext-dev-eastus` |
| **UI Dashboard** | Azure App Service | `app-clinext-dev-eastus-001` |
| **Secrets & Keys** | Azure Key Vault | `kv-clinext-dev-eastus` |
| **Monitoring & Telemetry** | Application Insights | `appi-clinext-dev-eastus` |
| **Zero-Trust Identity** | Managed Identity | `id-clinext-extractor-dev` |
| **AI Classifier & Extractor** | Azure OpenAI Account | `oai-vitals-dev-eastus` |
| **Core Compute** | Azure Function App | `func-vitals-extractor-dev` |
| **Workflow Coordinator** | Azure Logic App | `logic-vitals-pipeline-dev` |
| **Persistent Storage** | Azure Database for PostgreSQL | `psql-vitals-dev-eastus` |
| **UI Dashboard** | Azure App Service | `app-vitals-dev-eastus-001` |
| **Secrets & Keys** | Azure Key Vault | `kv-vitals-dev-eastus` |
| **Monitoring & Telemetry** | Application Insights | `appi-vitals-dev-eastus` |
| **Zero-Trust Identity** | Managed Identity | `id-vitals-extractor-dev` |

---

## 4. Mandatory Checklist Before Creating Any Resource

Before executing any `az` CLI command, Bicep file, or Azure SDK provisioning:
- [ ] Does the name start with the standardized prefix (e.g. `rg-`, `st`, `func-`, `logic-`, `kv-`)?
- [ ] Is it lowercase?
- [ ] Does it adhere to character limits (especially <= 24 characters for Storage and Key Vault)?
- [ ] For storage accounts, are hyphens omitted?
- [ ] Does it include the environment (`dev`) and region (`eastus`) where applicable?

