---
trigger: always_on
description: Mandatory Azure Resource Naming Conventions for all cloud resources, templates, and CLI scripts.
---

# Azure Resource Naming Rules

When generating Azure CLI commands, Bicep files, ARM templates, Terraform configurations, or Python SDK calls:

1. **Resource Group**: `rg-{app}-{env}-{region}` -> `rg-clinext-dev-eastus`
1. **Resource Group**: `rg-{app}-{env}` -> `rg-clinical-extract-dev`
2. **Storage Account**: `st{app}{env}{region}` -> `stclinextdeveastus` (Alphanumeric only, <= 24 characters, no hyphens)
1. **Resource Group**: `rg-{app}-{env}-{region}` -> `rg-vitals-dev-eastus`
2. **Storage Account**: `st{app}{env}{region}` -> `stvitalsdeveastus` (Alphanumeric only, <= 24 characters, no hyphens)
3. **Blob Container**: `{content-type}` -> `clinical-documents`
4. **Azure Function**: `func-{app}-{function}-{env}` -> `func-clinext-extractor-dev`
5. **Azure Logic App**: `logic-{app}-{process}-{env}` -> `logic-clinext-pipeline-dev`
6. **App Service (Web App)**: `app-{app}-{env}-{region}-{instance}` -> `app-clinext-dev-eastus-001`
7. **Key Vault**: `kv-{app}-{env}-{region}` -> `kv-clinext-dev-eastus` (<= 24 characters)
8. **PostgreSQL DB**: `psql-{app}-{env}-{region}` -> `psql-clinext-dev-eastus`
9. **Azure OpenAI**: `oai-{app}-{env}-{region}` -> `oai-clinext-dev-eastus`
10. **Managed Identity**: `id-{app}-{purpose}-{env}` -> `id-clinext-extractor-dev`

4. **Azure Function**: `func-{app}-{function}-{env}` -> `func-vitals-extractor-dev`
5. **Azure Logic App**: `logic-{app}-{process}-{env}` -> `logic-vitals-pipeline-dev`
6. **App Service (Web App)**: `app-{app}-{env}-{region}-{instance}` -> `app-vitals-dev-eastus-001`
7. **Key Vault**: `kv-{app}-{env}-{region}` -> `kv-vitals-dev-eastus` (<= 24 characters)
8. **PostgreSQL DB**: `psql-{app}-{env}-{region}` -> `psql-vitals-dev-eastus`
9. **Azure OpenAI**: `oai-{app}-{env}-{region}` -> `oai-vitals-dev-eastus`
10. **Managed Identity**: `id-{app}-{purpose}-{env}` -> `id-vitals-extractor-dev`
