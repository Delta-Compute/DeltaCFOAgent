"""
Invoice Attachment Manager
Handles file upload, storage, AI analysis, and retrieval for invoice attachments
"""

import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from werkzeug.utils import secure_filename

# Import payment proof processor for AI analysis (reuse existing Claude Vision integration)
from payment_proof_processor import PaymentProofProcessor


class AttachmentManager:
    """Manage invoice attachments with AI analysis"""

    # Allowed file extensions (accept all types as per requirement)
    ALLOWED_EXTENSIONS = {
        'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif', 'bmp', 'gif', 'webp',  # Images & PDFs
        'csv', 'xls', 'xlsx', 'xlsm',  # Spreadsheets
        'doc', 'docx', 'txt', 'rtf',  # Documents
        'zip', 'rar', '7z',  # Archives
        'eml', 'msg'  # Emails
    }

    # Base upload directory
    BASE_UPLOAD_DIR = 'uploads/attachments'

    def __init__(self, db_manager):
        """Initialize with database manager"""
        self.db_manager = db_manager
        self.payment_processor = PaymentProofProcessor()

    def upload_attachment(
        self,
        file_obj,
        invoice_id: str,
        tenant_id: str,
        attachment_type: str = 'other',
        description: str = None,
        uploaded_by: str = 'system',
        analyze_with_ai: bool = True
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Upload and store an attachment file

        Args:
            file_obj: FileStorage object from Flask request
            invoice_id: Invoice ID to attach to
            tenant_id: Tenant ID
            attachment_type: Type of attachment (payment_proof, invoice_pdf, supporting_doc, contract, other)
            description: Optional description
            uploaded_by: User who uploaded
            analyze_with_ai: Whether to analyze with Claude AI immediately

        Returns:
            Tuple of (success, message, attachment_data)
        """
        try:
            # Validate file
            if not file_obj or not file_obj.filename:
                return False, "No file provided", None

            original_filename = secure_filename(file_obj.filename)
            file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''

            if not file_ext:
                return False, "File has no extension", None

            # Create directory structure
            upload_dir = Path(self.BASE_UPLOAD_DIR) / tenant_id / invoice_id
            upload_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            new_filename = f"{timestamp}_{unique_id}_{original_filename}"
            file_path = upload_dir / new_filename

            # Save file
            file_obj.save(str(file_path))
            file_size = file_path.stat().st_size

            # Detect MIME type
            mime_type = self._get_mime_type(file_ext)

            # Store in database
            relative_path = str(file_path).replace('\\', '/')

            attachment_id = str(uuid.uuid4())
            insert_query = """
                INSERT INTO invoice_attachments (
                    id, invoice_id, tenant_id, attachment_type, file_name, file_path,
                    file_size, mime_type, description, uploaded_by, ai_analysis_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            self.db_manager.execute_query(
                insert_query,
                (attachment_id, invoice_id, tenant_id, attachment_type, original_filename,
                 relative_path, file_size, mime_type, description, uploaded_by, 'pending')
            )

            attachment_data = {
                'id': attachment_id,
                'invoice_id': invoice_id,
                'file_name': original_filename,
                'file_path': relative_path,
                'file_size': file_size,
                'mime_type': mime_type,
                'attachment_type': attachment_type,
                'ai_analysis_status': 'pending'
            }

            # Analyze with AI if requested and file type is supported
            if analyze_with_ai and self._is_analyzable(file_ext):
                success, analysis_result = self.analyze_attachment(attachment_id, tenant_id)
                if success:
                    attachment_data['ai_extracted_data'] = analysis_result
                    attachment_data['ai_analysis_status'] = 'analyzed'

            return True, "Attachment uploaded successfully", attachment_data

        except Exception as e:
            return False, f"Upload failed: {str(e)}", None

    def analyze_attachment(
        self,
        attachment_id: str,
        tenant_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Analyze attachment with Claude AI to extract payment data

        Args:
            attachment_id: Attachment ID to analyze
            tenant_id: Tenant ID

        Returns:
            Tuple of (success, extracted_data)
        """
        try:
            # Get attachment info
            query = """
                SELECT id, file_path, file_name, mime_type, attachment_type
                FROM invoice_attachments
                WHERE id = %s AND tenant_id = %s
            """
            attachment = self.db_manager.execute_query(query, (attachment_id, tenant_id), fetch_one=True)

            if not attachment:
                return False, None

            file_path = attachment['file_path']
            if not os.path.exists(file_path):
                return False, None

            # Use payment proof processor for AI analysis
            extracted_data = self.payment_processor.process_payment_proof(file_path, invoice_data=None)

            # Store extracted data
            update_query = """
                UPDATE invoice_attachments
                SET ai_extracted_data = %s,
                    ai_analysis_status = %s,
                    analyzed_at = CURRENT_TIMESTAMP
                WHERE id = %s AND tenant_id = %s
            """

            # Convert to JSON string for storage
            extracted_json = json.dumps(extracted_data)

            self.db_manager.execute_query(
                update_query,
                (extracted_json, 'analyzed', attachment_id, tenant_id)
            )

            return True, extracted_data

        except Exception as e:
            # Mark as failed
            try:
                self.db_manager.execute_query(
                    "UPDATE invoice_attachments SET ai_analysis_status = %s WHERE id = %s",
                    ('failed', attachment_id)
                )
            except:
                pass

            return False, None

    def list_attachments(
        self,
        invoice_id: str,
        tenant_id: str,
        attachment_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        List all attachments for an invoice

        Args:
            invoice_id: Invoice ID
            tenant_id: Tenant ID
            attachment_type: Optional filter by type

        Returns:
            List of attachment dictionaries
        """
        try:
            query = """
                SELECT id, invoice_id, attachment_type, file_name, file_path,
                       file_size, mime_type, description, ai_extracted_data,
                       ai_analysis_status, uploaded_by, uploaded_at, analyzed_at
                FROM invoice_attachments
                WHERE invoice_id = %s AND tenant_id = %s
            """
            params = [invoice_id, tenant_id]

            if attachment_type:
                query += " AND attachment_type = %s"
                params.append(attachment_type)

            query += " ORDER BY uploaded_at DESC"

            attachments = self.db_manager.execute_query(query, tuple(params), fetch_all=True)

            # Parse JSON data
            for att in attachments:
                if att.get('ai_extracted_data'):
                    try:
                        att['ai_extracted_data'] = json.loads(att['ai_extracted_data'])
                    except:
                        pass

            return attachments

        except Exception as e:
            print(f"Error listing attachments: {e}")
            return []

    def get_attachment(
        self,
        attachment_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get single attachment details

        Args:
            attachment_id: Attachment ID
            tenant_id: Tenant ID

        Returns:
            Attachment dictionary or None
        """
        try:
            query = """
                SELECT id, invoice_id, attachment_type, file_name, file_path,
                       file_size, mime_type, description, ai_extracted_data,
                       ai_analysis_status, uploaded_by, uploaded_at, analyzed_at
                FROM invoice_attachments
                WHERE id = %s AND tenant_id = %s
            """

            attachment = self.db_manager.execute_query(query, (attachment_id, tenant_id), fetch_one=True)

            if attachment and attachment.get('ai_extracted_data'):
                try:
                    attachment['ai_extracted_data'] = json.loads(attachment['ai_extracted_data'])
                except:
                    pass

            return attachment

        except Exception as e:
            print(f"Error getting attachment: {e}")
            return None

    def delete_attachment(
        self,
        attachment_id: str,
        tenant_id: str
    ) -> Tuple[bool, str]:
        """
        Delete an attachment

        Args:
            attachment_id: Attachment ID
            tenant_id: Tenant ID

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get attachment to delete file
            attachment = self.get_attachment(attachment_id, tenant_id)
            if not attachment:
                return False, "Attachment not found"

            file_path = attachment['file_path']

            # Delete from database first
            delete_query = """
                DELETE FROM invoice_attachments
                WHERE id = %s AND tenant_id = %s
            """
            self.db_manager.execute_query(delete_query, (attachment_id, tenant_id))

            # Delete file if exists
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Warning: Could not delete file {file_path}: {e}")

            return True, "Attachment deleted successfully"

        except Exception as e:
            return False, f"Delete failed: {str(e)}"

    def get_attachment_stats(
        self,
        invoice_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Get statistics about attachments for an invoice

        Args:
            invoice_id: Invoice ID
            tenant_id: Tenant ID

        Returns:
            Dictionary with stats
        """
        try:
            query = """
                SELECT
                    COUNT(*) as total_attachments,
                    SUM(file_size) as total_size,
                    COUNT(CASE WHEN attachment_type = 'payment_proof' THEN 1 END) as payment_proofs,
                    COUNT(CASE WHEN ai_analysis_status = 'analyzed' THEN 1 END) as analyzed,
                    COUNT(CASE WHEN ai_analysis_status = 'pending' THEN 1 END) as pending_analysis
                FROM invoice_attachments
                WHERE invoice_id = %s AND tenant_id = %s
            """

            stats = self.db_manager.execute_query(query, (invoice_id, tenant_id), fetch_one=True)
            return dict(stats) if stats else {}

        except Exception as e:
            print(f"Error getting attachment stats: {e}")
            return {}

    def _is_analyzable(self, file_ext: str) -> bool:
        """Check if file type can be analyzed by AI"""
        analyzable_types = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif', 'csv', 'xls', 'xlsx'}
        return file_ext.lower() in analyzable_types

    def _get_mime_type(self, file_ext: str) -> str:
        """Get MIME type from file extension"""
        mime_types = {
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'tiff': 'image/tiff',
            'tif': 'image/tiff',
            'csv': 'text/csv',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'txt': 'text/plain',
            'zip': 'application/zip'
        }
        return mime_types.get(file_ext.lower(), 'application/octet-stream')
