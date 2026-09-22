#!/bin/bash
# ==============================================================================
# Configure Azure App Service Environment Variables & Startup Command
# Web App: app-vitals-dev-centralindia-001
# Resource Group: rg-vitals-dev-centralindia
# ==============================================================================

set -e

echo "⚙️ Configuring Application Settings for app-vitals-dev-centralindia-001..."

az webapp config appsettings set \
  --resource-group rg-vitals-dev-centralindia \
  --name app-vitals-dev-centralindia-001 \
  --settings \
    DB_HOST="psql-vitals-dev-centralindia.postgres.database.azure.com" \
    DB_PORT="5432" \
    DB_NAME="postgres" \
    DB_USER="vitalsadmin" \
    DB_PASSWORD="AzureHealth#9876!" \
    DB_SSLMODE="require" \
    AZURE_STORAGE_CONTAINER_NAME="clinical-documents" \
    AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=stvitalsdevcentralindia;AccountKey=WJkJLPLDnvZPTJoH+YFWlE02fwvrPWfj633QX5dO9/7xOImXwfcjXORREbN5mV9Aa0JtwrUQ4SR9+AStlooYpw==;EndpointSuffix=core.windows.net" \
    AZURE_FUNCTION_URL="https://func-vitals-extractor-dev.azurewebsites.net/api/extract"

echo "🚀 Setting Startup Command to startup.sh..."
az webapp config set \
  --resource-group rg-vitals-dev-centralindia \
  --name app-vitals-dev-centralindia-001 \
  --startup-file "startup.sh"

echo "🔄 Restarting Web App container..."
az webapp restart \
  --resource-group rg-vitals-dev-centralindia \
  --name app-vitals-dev-centralindia-001

echo "✅ Configuration complete! Visit: https://app-vitals-dev-centralindia-001.azurewebsites.net"

