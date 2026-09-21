#!/usr/bin/env bash
# ==============================================================================
# MILESTONE 1: AZURE FOUNDATION & RESOURCE GROUP SETUP
# ==============================================================================
# Azure Concept:
# 1. Subscription: The billing container for your cloud resources.
# 2. Resource Group: A logical container holding related resources for an Azure
#    solution. It enables you to manage, monitor, and delete all resources together.
# 3. Region: The physical geographic location of Microsoft's datacenters.
#    (e.g., 'eastus' is ideal because it supports Azure OpenAI, Logic Apps, and Functions).
# ==============================================================================

set -euo pipefail

# Configuration variables adhering to docs/azure_naming_conventions.md
APP_NAME="vitals"
ENVIRONMENT="dev"
LOCATION="eastus"
RESOURCE_GROUP="rg-${APP_NAME}-${ENVIRONMENT}-${LOCATION}"   # rg-vitals-dev-eastus
PROJECT="Vitals"

echo "=== Step 1: Checking Azure CLI Authentication ==="
if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI ('az') is not installed."
    echo "To install on Ubuntu, run:"
    echo "  curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi

# Check if authenticated
ACCOUNT_INFO=$(az account show 2>/dev/null || true)
if [ -z "$ACCOUNT_INFO" ]; then
    echo "You are not logged in. Initiating login..."
    az login
fi

# Display current active subscription
echo "=== Step 2: Active Azure Subscription ==="
CURRENT_SUB_ID=$(az account show --query "id" -o tsv)
CURRENT_SUB_NAME=$(az account show --query "name" -o tsv)
echo "Subscription Name: $CURRENT_SUB_NAME"
echo "Subscription ID:   $CURRENT_SUB_ID"

# Step 3: Create Resource Group
echo "=== Step 3: Creating Resource Group '$RESOURCE_GROUP' in '$LOCATION' ==="
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --tags Environment="$ENVIRONMENT" Project="$PROJECT" ManagedBy="AzureCLI" \
    --output table

echo ""
echo "✅ Milestone 1 Complete!"
echo "Resource Group '$RESOURCE_GROUP' is active and ready."
echo "You can verify this in the Azure Portal at: https://portal.azure.com/#browse/resourcegroups"

