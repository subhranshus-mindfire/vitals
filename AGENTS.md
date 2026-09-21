# Agent Rules: Azure Resource Naming & Infrastructure Standards

This file is automatically loaded by the Antigravity agent on every interaction within this workspace.

## MANDATORY RULE: Azure Resource Naming Conventions
Whenever creating, proposing, or modifying any Azure resource, script, Bicep file, Terraform module, or Azure CLI command, you **MUST** strictly follow the project's Azure Naming Conventions defined below.

### 1. General Principles
- Use lowercase letters, numbers, and hyphens only (`[a-z0-9-]`).
- **No hyphens** in Storage Accounts and Container Registries (alphanumeric only).
- Start and end with an alphanumeric character. Never use consecutive hyphens (`--`).
- Respect character length limits (keep names under 24 characters where required, especially Storage Accounts and Key Vaults).
- Use standard abbreviations:
  - App Name: `clinext`
  - App Name: `vitals`
  - Environment: `dev` (default for learning/development), `test`, `prod`
  - Region: `eastus` (default), `westeu`
  - Instance: `001`

### 2. Standard Resource Name Matrix for this Project (`dev`, `eastus`)
| Resource Type | Convention / Pattern | Required Name for this Project |
|---|---|---|
| **Resource Group** | `rg-{app}-{env}-{region}` | `rg-clinext-dev-eastus` |
| **Resource Group** | `rg-{app}-{env}` | `rg-clinical-extract-dev` |
| **Storage Account** | `st{app}{env}{region}` | `stclinextdeveastus` (<= 24 chars, no hyphens) |
| **Resource Group** | `rg-{app}-{env}-{region}` | `rg-vitals-dev-eastus` |
| **Storage Account** | `st{app}{env}{region}` | `stvitalsdeveastus` (<= 24 chars, no hyphens) |
| **Blob Container** | `{content-type}` | `clinical-documents` |
| **Azure Function App** | `func-{app}-{function}-{env}` | `func-clinext-extractor-dev` |
| **Azure Logic App** | `logic-{app}-{process}-{env}` | `logic-clinext-pipeline-dev` |
| **Web App (App Service)** | `app-{app}-{env}-{region}-{instance}` | `app-clinext-dev-eastus-001` |
| **App Service Plan** | `asp-{app}-{env}-{region}` | `asp-clinext-dev-eastus` |
| **Key Vault** | `kv-{app}-{env}-{region}` | `kv-clinext-dev-eastus` (<= 24 chars) |
| **Key Vault Secret** | `secret-{app}-{description}` | `secret-clinext-{description}` |
| **PostgreSQL Database** | `psql-{app}-{env}-{region}` | `psql-clinext-dev-eastus` |
| **Azure OpenAI Service** | `oai-{app}-{env}-{region}` | `oai-clinext-dev-eastus` |
| **User Managed Identity** | `id-{app}-{purpose}-{env}` | `id-clinext-extractor-dev` |
| **Application Insights** | `appi-{app}-{env}-{region}` | `appi-clinext-dev-eastus` |
| **Log Analytics Workspace**| `log-{app}-{env}-{region}` | `log-clinext-dev-eastus` |
| **Azure Function App** | `func-{app}-{function}-{env}` | `func-vitals-extractor-dev` |
| **Azure Logic App** | `logic-{app}-{process}-{env}` | `logic-vitals-pipeline-dev` |
| **Web App (App Service)** | `app-{app}-{env}-{region}-{instance}` | `app-vitals-dev-eastus-001` |
| **App Service Plan** | `asp-{app}-{env}-{region}` | `asp-vitals-dev-eastus` |
| **Key Vault** | `kv-{app}-{env}-{region}` | `kv-vitals-dev-eastus` (<= 24 chars) |
| **Key Vault Secret** | `secret-{app}-{description}` | `secret-vitals-{description}` |
| **PostgreSQL Database** | `psql-{app}-{env}-{region}` | `psql-vitals-dev-eastus` |
| **Azure OpenAI Service** | `oai-{app}-{env}-{region}` | `oai-vitals-dev-eastus` |
| **User Managed Identity** | `id-{app}-{purpose}-{env}` | `id-vitals-extractor-dev` |
| **Application Insights** | `appi-{app}-{env}-{region}` | `appi-vitals-dev-eastus` |
| **Log Analytics Workspace**| `log-{app}-{env}-{region}` | `log-vitals-dev-eastus` |

Reference Document: [docs/azure_naming_conventions.md](file:///home/subhranshus/Projects/Azure/docs/azure_naming_conventions.md)

