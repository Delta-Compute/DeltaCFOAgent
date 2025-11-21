# Google Cloud Storage File Upload System - Implementation Guide

## Overview

This guide documents the implementation of a persistent file storage system using Google Cloud Storage (GCS) for the DeltaCFOAgent multi-tenant SaaS platform. All user-uploaded files (CSV, PDF, Excel, images) are now stored permanently in GCS with full tenant isolation.

---

## What's Been Completed

### Phase 2: File Storage Service ✅ COMPLETE
**File Created:** `/web_ui/services/file_storage_service.py`

Complete GCS-only file storage service with:
- **Tenant isolation**: Files organized as `{tenant_id}/{document_type}/{filename}`
- **File validation**: Type and size checking
- **MD5 hashing**: File integrity verification
- **Signed URLs**: Secure time-limited downloads
- **Database tracking**: All uploads recorded in `tenant_documents` table

**Key Methods:**
- `save_file()` - Upload file to GCS and record in database
- `get_file()` - Download file contents with tenant verification
- `get_signed_url()` - Generate secure download URL (60 min expiry)
- `delete_file()` - Remove from GCS and database
- `list_files()` - Paginated file listing per tenant

### Phase 3: Database Migration ✅ COMPLETE
**Files Created:**
- `/migrations/add_file_hash_metadata_columns.sql`
- `/migrations/apply_file_storage_migration.py`

**Changes Applied:**
- Added `file_hash` column (VARCHAR 64) - for MD5 integrity checks
- Added `metadata` column (JSONB) - for additional file information
- Created indexes:
  - `idx_tenant_documents_tenant_type` - Fast queries by tenant + type
  - `idx_tenant_documents_hash` - File deduplication support

**Migration Status:** Applied successfully to delta_cfo database

### Phase 6: Dependencies ✅ COMPLETE
**File Modified:** `/requirements.txt`

Added: `google-cloud-storage>=2.10.0`
Status: Already installed (version 3.4.0)

---

## What Needs To Be Done Next

### Phase 1: Create GCS Buckets (MANUAL STEP REQUIRED)

You need to create the GCS buckets before the system can work. Run these commands in your terminal:

```bash
# 1. Reauthenticate with gcloud
gcloud auth login

# 2. Set project
gcloud config set project aicfo-473816

# 3. Create development bucket
gsutil mb -l southamerica-east1 gs://deltacfo-uploads-dev

# 4. Create production bucket
gsutil mb -l southamerica-east1 gs://deltacfo-uploads-prod

# 5. Set lifecycle policy for development (90 days retention)
cat > lifecycle-dev.json <<'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle-dev.json gs://deltacfo-uploads-dev

# 6. Set lifecycle policy for production (7 years / 2555 days)
cat > lifecycle-prod.json <<'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 2555}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle-prod.json gs://deltacfo-uploads-prod

# 7. Enable versioning for production (audit trail)
gsutil versioning set on gs://deltacfo-uploads-prod

# 8. Grant permissions to Cloud Run service account
gsutil iam ch serviceAccount:620026562181-compute@developer.gserviceaccount.com:objectAdmin gs://deltacfo-uploads-dev
gsutil iam ch serviceAccount:620026562181-compute@developer.gserviceaccount.com:objectAdmin gs://deltacfo-uploads-prod
```

### Phase 4: Update Upload Endpoints in app_db.py (CODE CHANGES)

You need to update all file upload endpoints to use the new GCS storage service instead of `/tmp`.

**Find these locations in `app_db.py`:**
- Line ~12033: Transaction CSV upload
- Line ~12298: Invoice PDF upload
- Any other upload endpoints

**OLD CODE (to be replaced):**
```python
temp_path = os.path.join('/tmp' if os.name != 'nt' else os.environ.get('TEMP', 'C:\\temp'), filename)
file.save(temp_path)
# ... process file ...
os.remove(temp_path)  # DELETE THIS LINE
```

**NEW CODE (replacement):**
```python
from services.file_storage_service import file_storage

try:
    # Save to GCS with tenant isolation
    gcs_uri, document_info = file_storage.save_file(
        file_obj=file,
        document_type='transactions',  # or 'invoices', 'statements', etc.
        user_id=session.get('user_id'),
        metadata={
            'description': request.form.get('description', ''),
            'source': 'web_upload'
        }
    )

    # Get file contents for processing
    file_bytes = file_storage.get_file(document_info['id'])

    # Process file (e.g., parse CSV)
    import pandas as pd
    import io
    df = pd.read_csv(io.BytesIO(file_bytes))

    # ... rest of processing logic ...

    # DO NOT DELETE FILE - it's permanently stored in GCS

    return jsonify({
        'success': True,
        'document_id': document_info['id'],
        'filename': document_info['original_filename']
    })

except ValueError as e:
    return jsonify({'error': str(e)}), 400
```

### Phase 5: Add File Management API Endpoints (CODE CHANGES)

Add these new API endpoints to `app_db.py`:

```python
from services.file_storage_service import file_storage

@app.route('/api/documents', methods=['GET'])
def get_documents():
    """List all documents for current tenant"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        document_type = request.args.get('type')

        result = file_storage.list_files(
            document_type=document_type,
            page=page,
            per_page=per_page
        )

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/documents/<document_id>/download', methods=['GET'])
def download_document(document_id):
    """Get signed URL for document download"""
    try:
        expiration_minutes = request.args.get('expiration', 60, type=int)

        signed_url = file_storage.get_signed_url(
            document_id,
            expiration_minutes=expiration_minutes
        )

        if not signed_url:
            return jsonify({'error': 'Document not found'}), 404

        return jsonify({
            'download_url': signed_url,
            'expires_in_minutes': expiration_minutes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/documents/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    """Delete document"""
    try:
        success = file_storage.delete_file(document_id)

        if not success:
            return jsonify({'error': 'Document not found'}), 404

        return jsonify({'message': 'Document deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## Environment Configuration

### Development (.env)
Add these variables to your `.env` file:

```bash
# Google Cloud Storage Configuration
GCS_BUCKET_NAME=deltacfo-uploads-dev
GCS_PROJECT_ID=aicfo-473816
UPLOAD_MAX_SIZE_MB=50
UPLOAD_RETENTION_DAYS=90
```

### Production (Cloud Run Environment Variables)
Update `cloudbuild.yaml` or set via Cloud Console:

```yaml
env:
  - GCS_BUCKET_NAME=deltacfo-uploads-prod
  - GCS_PROJECT_ID=aicfo-473816
  - UPLOAD_MAX_SIZE_MB=50
  - UPLOAD_RETENTION_DAYS=2555
```

---

## Authentication Setup

### For Local Development

Run this once on your local machine:

```bash
# Authenticate with your Google Cloud account
gcloud auth application-default login

# Verify credentials
gcloud auth application-default print-access-token
```

This creates credentials at `~/.config/gcloud/application_default_credentials.json` that the Python client will automatically use.

### For Production (Cloud Run)

The Cloud Run service account (620026562181-compute@developer.gserviceaccount.com) is already configured and will have access once you grant permissions to the buckets (see Phase 1).

---

## Testing Checklist

Once you complete Phases 1, 4, and 5, test the following:

### Development Tests (deltacfo-uploads-dev)
- [ ] Upload CSV transaction file → verify appears in GCS bucket
- [ ] Upload PDF invoice → verify appears in GCS bucket
- [ ] List documents via `/api/documents` → verify tenant isolation
- [ ] Download document via signed URL → verify file served correctly
- [ ] Delete document → verify removed from GCS and database
- [ ] Try uploading 51MB file → should fail with size limit error
- [ ] Try uploading .exe file → should fail with type validation error
- [ ] Verify MD5 hash is stored correctly

### Multi-Tenant Isolation Tests
- [ ] User A uploads file → User B cannot see it
- [ ] User A cannot download User B's document_id
- [ ] User A cannot delete User B's document_id
- [ ] GCS paths correctly namespaced by tenant_id (check GCS console)

### Production Tests (after deployment)
- [ ] Same tests as development on production bucket
- [ ] Verify lifecycle policy (check GCS console - files marked for deletion after 2555 days)
- [ ] Verify versioning enabled (upload same file twice, check versions)
- [ ] Test concurrent uploads from multiple tenants

---

## File Organization in GCS

Files are organized with the following structure:

```
gs://deltacfo-uploads-dev/  (or deltacfo-uploads-prod)
  ├── delta/                     # Tenant ID
  │   ├── transactions/          # Document type
  │   │   ├── uuid1_file1.csv
  │   │   └── uuid2_file2.xlsx
  │   ├── invoices/
  │   │   ├── uuid3_invoice1.pdf
  │   │   └── uuid4_invoice2.pdf
  │   ├── receipts/
  │   └── statements/
  ├── acme_corp/                 # Another tenant
  │   ├── transactions/
  │   └── invoices/
  └── ...
```

**Benefits:**
- Complete tenant isolation at filesystem level
- Easy to audit and debug
- Scalable to unlimited tenants
- Simple backup/restore per tenant

---

## Security Features

1. **Tenant Isolation**: Every operation verifies tenant_id - User A cannot access User B's files
2. **Signed URLs**: Download links expire after 60 minutes (configurable)
3. **File Validation**: Type and size checking before upload
4. **MD5 Integrity**: Detect file corruption or tampering
5. **IAM Permissions**: Only authorized service account can access buckets
6. **Audit Trail**: All operations logged in `tenant_documents` table

---

## Rollback Plan

If you encounter issues:

1. **Disable GCS temporarily**: Comment out GCS upload code, use /tmp fallback
2. **Files are safe**: Data in GCS buckets remains intact
3. **Database tracking**: All file records preserved in tenant_documents table
4. **Easy revert**: Simply switch back to new code when ready

---

## Supported File Types

### By Document Type:
- **transactions**: csv, xlsx, xls
- **invoices**: pdf
- **statements**: pdf, csv
- **receipts**: jpg, jpeg, png, pdf
- **contracts**: pdf, docx, doc
- **other**: csv, pdf, xlsx, xls, jpg, jpeg, png, txt

To add new types, edit `ALLOWED_EXTENSIONS` in `/web_ui/services/file_storage_service.py`

---

## Cost Considerations

### Development Bucket (deltacfo-uploads-dev)
- **Lifecycle**: Files deleted after 90 days
- **Expected Cost**: ~$0.02/GB/month (South America East1)
- **Free Tier**: 5GB storage + 5,000 operations/month

### Production Bucket (deltacfo-uploads-prod)
- **Lifecycle**: Files deleted after 2555 days (7 years - financial compliance)
- **Versioning**: Enabled (previous versions count toward storage)
- **Expected Cost**: Depends on usage, estimate ~$0.02/GB/month

**Tip**: Monitor usage in GCS console to avoid surprises

---

## Next Steps Summary

1. **NOW**: Create GCS buckets (Phase 1 commands above)
2. **NOW**: Add GCS_BUCKET_NAME to .env file
3. **NEXT**: Update upload endpoints in app_db.py (Phase 4)
4. **NEXT**: Add file management API endpoints (Phase 5)
5. **THEN**: Test thoroughly (use checklist above)
6. **FINALLY**: Deploy to production with updated environment variables

---

## Files Modified/Created

### Created:
- `/web_ui/services/file_storage_service.py` - GCS file storage service
- `/migrations/add_file_hash_metadata_columns.sql` - Database migration
- `/migrations/apply_file_storage_migration.py` - Migration script
- `/GCS_FILE_STORAGE_SETUP.md` - This guide

### Modified:
- `/requirements.txt` - Added google-cloud-storage>=2.10.0
- Database: tenant_documents table (added file_hash, metadata columns)

### To Be Modified:
- `/web_ui/app_db.py` - Update upload endpoints (Phase 4 & 5)
- `.env` - Add GCS_BUCKET_NAME variable
- `cloudbuild.yaml` - Add GCS environment variables for production

---

## Support

If you encounter issues:

1. Check GCS bucket exists: `gsutil ls gs://deltacfo-uploads-dev`
2. Verify permissions: `gsutil iam get gs://deltacfo-uploads-dev`
3. Test authentication: `gcloud auth application-default print-access-token`
4. Check logs: Cloud Run logs or local Flask console
5. Verify database migration: Check tenant_documents table has file_hash column

---

## Architecture Decision

**Why GCS-Only (No Local Filesystem)?**
- **Consistency**: Same code in dev and prod
- **Simplicity**: No dual-backend complexity
- **Cost-Effective**: GCS free tier covers development
- **Scalability**: No disk space limits
- **Team Collaboration**: Shared file access
- **Zero Infrastructure**: No need to manage volumes or persistent disks

This approach eliminates "works on my machine" issues and ensures production-like testing in development.
