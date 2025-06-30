import logging
import os
import json
import azure.functions as func
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta

def main(event: func.EventGridEvent):
    try:
        event_data = event.get_json()
        source_blob_url = event_data['url']
        source_container = source_blob_url.split("/")[-2]
        blob_name = source_blob_url.split("/")[-1]

        logging.info(f"Processing blob: {blob_name} in container: {source_container}")

        primary_conn_str = os.environ["PRIMARY_STORAGE_CONNECTION_STRING"]
        secondary_conn_str = os.environ["SECONDARY_STORAGE_CONNECTION_STRING"]
        secondary_container = os.environ.get("SECONDARY_CONTAINER_NAME", "secondary-backup-container")

        primary_client = BlobServiceClient.from_connection_string(primary_conn_str)
        secondary_client = BlobServiceClient.from_connection_string(secondary_conn_str)

        source_blob = primary_client.get_blob_client(container=source_container, blob=blob_name)

        sas_token = generate_blob_sas(
            account_name=source_blob.account_name,
            container_name=source_blob.container_name,
            blob_name=source_blob.blob_name,
            account_key=primary_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)
        )

        destination_blob = secondary_client.get_blob_client(container=secondary_container, blob=blob_name)
        destination_blob.start_copy_from_url(f"{source_blob_url}?{sas_token}")

        logging.info(f"Successfully replicated blob: {blob_name}")

    except Exception as e:
        logging.error(f"Replication failed: {e}")
