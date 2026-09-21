"""
Azure Blob Storage Service for the Vitals Clinical Platform.

Handles:
1. Uploading raw clinical documents (PDF, TXT, images) to Azure Blob Storage.
2. Generating secure, time-limited Shared Access Signature (SAS) tokens for read access.
3. Downloading and streaming documents for AI processing.
4. Listing stored clinical documents.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
import os

from azure.storage.blob import (
    BlobServiceClient,
    BlobClient,
    ContainerClient,
    BlobSasPermissions,
    generate_blob_sas,
    ContentSettings,
)


class AzureBlobStorageService:
    """Encapsulates Azure Blob Storage operations for clinical documents."""

    def __init__(self, connection_string: Optional[str] = None, container_name: str = "clinical-documents"):
        self.connection_string = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = container_name or os.getenv("AZURE_STORAGE_CONTAINER_NAME", "clinical-documents")

        if not self.connection_string:
            raise ValueError(
                "Missing Azure Storage connection string. "
                "Set AZURE_STORAGE_CONNECTION_STRING environment variable or pass it to constructor."
            )

        self.blob_service_client: BlobServiceClient = BlobServiceClient.from_connection_string(
            self.connection_string
        )
        self.container_client: ContainerClient = self.blob_service_client.get_container_client(
            self.container_name
        )

    def upload_document(
        self,
        blob_name: str,
        data: bytes,
        content_type: str = "text/plain",
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Uploads a raw clinical document to Azure Blob Storage.
        
        Args:
            blob_name: Target blob name/path (e.g. 'patients/PT-90214/visit_note.txt')
            data: File bytes to upload
            content_type: MIME type (e.g. 'application/pdf', 'text/plain')
            metadata: Custom key-value pairs (e.g. {'patient_id': 'PT-90214'})

        Returns:
            The primary URL of the uploaded blob.
        """
        blob_client: BlobClient = self.container_client.get_blob_client(blob_name)
        content_settings = ContentSettings(content_type=content_type)

        blob_client.upload_blob(
            data,
            overwrite=True,
            content_settings=content_settings,
            metadata=metadata or {},
        )
        return blob_client.url

    def download_document_text(self, blob_name: str) -> str:
        """Downloads a text-based clinical document as a decoded string."""
        blob_client: BlobClient = self.container_client.get_blob_client(blob_name)
        download_stream = blob_client.download_blob()
        return download_stream.readall().decode("utf-8")

    def generate_sas_url(self, blob_name: str, expiry_minutes: int = 30) -> str:
        """
        Generates a secure, short-lived Shared Access Signature (SAS) URL.
        
        This URL allows secure, temporary read access without exposing 
        account master keys or making the container publicly accessible.
        """
        blob_client: BlobClient = self.container_client.get_blob_client(blob_name)
        
        # Extract account name and key from connection string
        account_name = self.blob_service_client.account_name
        account_key = self.blob_service_client.credential.account_key

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        )

        return f"{blob_client.url}?{sas_token}"

    def list_documents(self) -> List[dict]:
        """Lists all blobs in the clinical-documents container with metadata."""
        blob_list = []
        for blob in self.container_client.list_blobs(include=["metadata"]):
            blob_list.append({
                "name": blob.name,
                "size_bytes": blob.size,
                "last_modified": blob.last_modified,
                "content_type": blob.content_settings.content_type if blob.content_settings else None,
                "metadata": blob.metadata,
            })
        return blob_list

