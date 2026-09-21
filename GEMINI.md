# Workspace Guidelines: Azure Infrastructure Standards

Always adhere to the Azure Resource Naming Conventions defined in `AGENTS.md` and `docs/azure_naming_conventions.md`.
Never create ad-hoc or unformatted resource names.
Always use prefixes (`rg-`, `st`, `func-`, `logic-`, `app-`, `kv-`, `psql-`, `id-`), enforce lowercase, keep under 24 chars for storage/keyvault, and maintain the `{app}-{env}-{region}` taxonomy.

