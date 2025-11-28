#!/usr/bin/env python3
"""
Google Cloud Storage File Service for Multi-Tenant SaaS
Handles secure file uploads with tenant isolation
"""

import os
import uuid
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple, BinaryIO
from werkzeug.utils import secure_filename
from google.cloud import storage
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from database import db_manager
from tenant_context import get_current_tenant_id

class FileStorageService:
    """
    Manages persistent file storage in Google Cloud Storage with tenant isolation
    """

    ALLOWED_EXTENSIONS = {
        'transactions': {'csv', 'xlsx', 'xls'},
        'invoices': {'pdf'},
        'statements': {'pdf', 'csv'},
        'receipts': {'jpg', 'jpeg', 'png', 'pdf'},
        'contracts': {'pdf', 'docx', 'doc'},
        'other': {'csv', 'pdf', 'xlsx', 'xls', 'jpg', 'jpeg', 'png', 'txt'}
    }

    def __init__(self):
        """Initialize GCS client and bucket with service account authentication"""
        # Get service account credentials
        credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

        # If not set in environment, look for service account file in project root
        if not credentials_path:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            service_account_path = os.path.join(project_root, 'firebase-service-account.json')

            if os.path.exists(service_account_path):
                credentials_path = service_account_path
                print(f"Using service account from: {credentials_path}")

        # Initialize GCS client with explicit credentials
        if credentials_path and os.path.exists(credentials_path):
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            self.gcs_client = storage.Client(credentials=credentials)
            print(f"✅ GCS client initialized with service account: {credentials_path}")
        else:
            # Fallback to Application Default Credentials (for development)
            self.gcs_client = storage.Client()
            print("⚠️ GCS client initialized with Application Default Credentials")

        self.bucket_name = os.environ.get('GCS_BUCKET_NAME')

        if not self.bucket_name:
            raise ValueError(
                "GCS_BUCKET_NAME environment variable not set. "
                "Set to 'deltacfo-uploads-dev' for development or "
                "'deltacfo-uploads-prod' for production."
            )

        self.bucket = self.gcs_client.bucket(self.bucket_name)
        self.max_size_mb = int(os.environ.get('UPLOAD_MAX_SIZE_MB', 50))

    def _validate_file(self, file_obj, document_type: str) -> Tuple[str, str, int]:
        """
        Validate file type and size

        Returns:
            Tuple of (original_filename, file_extension, file_size)
        """
        original_filename = secure_filename(file_obj.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else None

        # Validate extension
        allowed_exts = self.ALLOWED_EXTENSIONS.get(document_type, set())
        if not file_ext or file_ext not in allowed_exts:
            raise ValueError(
                f"Invalid file type '.{file_ext}' for document type '{document_type}'. "
                f"Allowed: {', '.join(allowed_exts)}"
            )

        # Validate size
        file_obj.seek(0, os.SEEK_END)
        file_size = file_obj.tell()
        file_obj.seek(0)

        max_size_bytes = self.max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise ValueError(
                f"File size ({file_size / 1024 / 1024:.2f}MB) exceeds "
                f"maximum allowed size ({self.max_size_mb}MB)"
            )

        return original_filename, file_ext, file_size

    def _calculate_hash(self, file_obj: BinaryIO) -> str:
        """Calculate MD5 hash of file for integrity checking"""
        file_obj.seek(0)
        file_hash = hashlib.md5(file_obj.read()).hexdigest()
        file_obj.seek(0)
        return file_hash

    def save_file(
        self,
        file_obj,
        document_type: str,
        tenant_id: str = None,
        user_id: str = None,
        metadata: dict = None
    ) -> Tuple[str, dict]:
        """
        Save uploaded file to Google Cloud Storage with tenant isolation

        Args:
            file_obj: Werkzeug FileStorage object
            document_type: Type of document (transactions, invoices, etc.)
            tenant_id: Tenant ID (defaults to current tenant from session)
            user_id: User who uploaded the file
            metadata: Additional metadata (description, tags, etc.)

        Returns:
            Tuple of (gcs_uri, document_record)

        Raises:
            ValueError: Invalid file type, size, or missing tenant context
        """
        # Get tenant context
        tenant_id = tenant_id or get_current_tenant_id()
        if not tenant_id:
            raise ValueError("Tenant context not set - user must be authenticated")

        # Validate file
        original_filename, file_ext, file_size = self._validate_file(file_obj, document_type)

        # Calculate file hash
        file_hash = self._calculate_hash(file_obj)

        # Generate unique filename
        file_uuid = str(uuid.uuid4())
        unique_filename = f"{file_uuid}_{original_filename}"

        # Build GCS path: {tenant_id}/{document_type}/{unique_filename}
        gcs_path = f"{tenant_id}/{document_type}/{unique_filename}"

        # Upload to GCS
        blob = self.bucket.blob(gcs_path)

        # Set metadata on blob
        blob.metadata = {
            'tenant_id': tenant_id,
            'document_type': document_type,
            'original_filename': original_filename,
            'uploaded_by': user_id or 'unknown',
            'file_hash': file_hash
        }

        # Upload file
        file_obj.seek(0)
        blob.upload_from_file(
            file_obj,
            content_type=file_obj.content_type,
            timeout=300  # 5 minutes for large files
        )

        # Full GCS URI
        gcs_uri = f"gs://{self.bucket_name}/{gcs_path}"

        # Save to database
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Convert metadata dict to JSON string for JSONB column
            metadata_json = json.dumps(metadata) if metadata else None

            cursor.execute("""
                INSERT INTO tenant_documents (
                    tenant_id,
                    document_name,
                    document_type,
                    file_path,
                    file_size,
                    mime_type,
                    uploaded_by_user_id,
                    file_hash,
                    metadata,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                tenant_id,
                original_filename,
                document_type,
                gcs_uri,
                file_size,
                file_obj.content_type,
                user_id,
                file_hash,
                metadata_json,  # JSONB field
                datetime.utcnow()
            ))

            document_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()

        return gcs_uri, {
            'id': str(document_id),
            'gcs_path': gcs_path,
            'gcs_uri': gcs_uri,
            'original_filename': original_filename,
            'file_size': file_size,
            'file_hash': file_hash
        }

    def get_file(self, document_id: str, tenant_id: str = None) -> Optional[bytes]:
        """
        Get file contents from GCS with tenant verification

        Returns:
            File contents as bytes, or None if not found
        """
        tenant_id = tenant_id or get_current_tenant_id()

        # Get file path from database with tenant verification
        gcs_uri = self._get_file_path(document_id, tenant_id)
        if not gcs_uri:
            return None

        # Extract blob path from URI
        blob_path = gcs_uri.replace(f"gs://{self.bucket_name}/", "")

        # Download from GCS
        blob = self.bucket.blob(blob_path)

        if not blob.exists():
            return None

        return blob.download_as_bytes()

    def get_signed_url(
        self,
        document_id: str,
        tenant_id: str = None,
        expiration_minutes: int = 60
    ) -> Optional[str]:
        """
        Generate signed URL for secure file download

        Args:
            document_id: Document ID
            tenant_id: Tenant ID (defaults to current tenant)
            expiration_minutes: URL expiration time in minutes

        Returns:
            Signed URL string, or None if file not found
        """
        tenant_id = tenant_id or get_current_tenant_id()

        # Get file path from database with tenant verification
        gcs_uri = self._get_file_path(document_id, tenant_id)
        if not gcs_uri:
            return None

        # Extract blob path from URI
        blob_path = gcs_uri.replace(f"gs://{self.bucket_name}/", "")

        # Generate signed URL
        blob = self.bucket.blob(blob_path)

        if not blob.exists():
            return None

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="GET"
        )

        return url

    def _get_file_path(self, document_id: str, tenant_id: str) -> Optional[str]:
        """Get GCS URI for a document ID with tenant verification"""
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT file_path
                FROM tenant_documents
                WHERE id = %s AND tenant_id = %s
            """, (document_id, tenant_id))

            result = cursor.fetchone()
            cursor.close()

            return result[0] if result else None

    def delete_file(self, document_id: str, tenant_id: str = None) -> bool:
        """
        Delete file from GCS and database with tenant verification

        Returns:
            True if deleted, False if not found
        """
        tenant_id = tenant_id or get_current_tenant_id()

        # Get file path from database
        gcs_uri = self._get_file_path(document_id, tenant_id)
        if not gcs_uri:
            return False

        # Extract blob path from URI
        blob_path = gcs_uri.replace(f"gs://{self.bucket_name}/", "")

        # Delete from GCS
        try:
            blob = self.bucket.blob(blob_path)
            if blob.exists():
                blob.delete()
        except Exception as e:
            print(f"Warning: Could not delete GCS file {blob_path}: {e}")

        # Delete from database
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM tenant_documents
                WHERE id = %s AND tenant_id = %s
            """, (document_id, tenant_id))

            deleted = cursor.rowcount > 0
            conn.commit()
            cursor.close()

        return deleted

    def rename_file(self, document_id: str, new_name: str, tenant_id: str = None) -> bool:
        """
        Rename a file's display name in the database (GCS path unchanged)

        Args:
            document_id: Document ID to rename
            new_name: New display name for the file
            tenant_id: Tenant ID (defaults to current tenant)

        Returns:
            True if renamed successfully, False if not found

        Note:
            This only updates the display name in the database.
            The actual GCS file path remains unchanged for integrity.
        """
        tenant_id = tenant_id or get_current_tenant_id()
        if not tenant_id:
            raise ValueError("Tenant context not set - user must be authenticated")

        # Sanitize new name
        new_name = secure_filename(new_name.strip())
        if not new_name:
            raise ValueError("Invalid file name")

        # Update database record
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE tenant_documents
                SET document_name = %s,
                    updated_at = %s
                WHERE id = %s AND tenant_id = %s
            """, (new_name, datetime.utcnow(), document_id, tenant_id))

            updated = cursor.rowcount > 0
            conn.commit()
            cursor.close()

        return updated

    def list_files(
        self,
        tenant_id: str = None,
        document_type: str = None,
        page: int = 1,
        per_page: int = 50
    ) -> dict:
        """
        List files for a tenant with pagination

        Returns:
            Dictionary with files list and pagination info
        """
        tenant_id = tenant_id or get_current_tenant_id()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Build query
            query = """
                SELECT id, document_name, document_type, file_size,
                       mime_type, uploaded_by_user_id, created_at, file_hash
                FROM tenant_documents
                WHERE tenant_id = %s
            """
            params = [tenant_id]

            if document_type:
                query += " AND document_type = %s"
                params.append(document_type)

            # Count total
            count_query = query.replace(
                "SELECT id, document_name, document_type, file_size, mime_type, uploaded_by_user_id, created_at, file_hash",
                "SELECT COUNT(*)"
            )
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # Get paginated results
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([per_page, (page - 1) * per_page])

            cursor.execute(query, params)
            files = cursor.fetchall()
            cursor.close()

        return {
            'files': [
                {
                    'id': str(f[0]),
                    'name': f[1],
                    'type': f[2],
                    'size': f[3],
                    'mime_type': f[4],
                    'uploaded_by': f[5],
                    'uploaded_at': f[6].isoformat() if f[6] else None,
                    'hash': f[7]
                }
                for f in files
            ],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }

# Global instance
file_storage = FileStorageService()
