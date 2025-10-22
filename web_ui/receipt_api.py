#!/usr/bin/env python3
"""
Receipt Upload API Endpoints
Handles receipt file upload, processing, matching, and linking
"""

import os
import logging
from datetime import datetime
from flask import request, jsonify, send_file
from werkzeug.utils import secure_filename
import uuid

logger = logging.getLogger(__name__)

# In-memory storage for receipts (temporary - will move to database/cloud storage)
receipts_storage = {}
receipt_matches_cache = {}


def register_receipt_routes(app):
    """Register receipt API routes with the Flask app"""

    @app.route('/api/receipts/upload', methods=['POST'])
    def api_upload_receipt():
        """
        Upload and process a receipt file

        Form Data:
            file: Receipt file (PDF, PNG, JPG, HEIC, etc.)
            auto_process: bool (optional) - Process immediately (default: true)

        Returns:
            receipt_id: str
            filename: str
            file_size: int
            file_type: str
            upload_at: str
            status: str ('uploaded' or 'processed')
            extracted_data: dict (if auto_process=true)
            matches: list (if auto_process=true)
        """
        try:
            # Check for file
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400

            # Auto-process flag (default: true)
            auto_process = request.form.get('auto_process', 'true').lower() == 'true'

            # Secure the filename
            original_filename = secure_filename(file.filename)
            file_ext = os.path.splitext(original_filename)[1].lower()

            # Validate file type
            allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.heic', '.webp', '.tiff', '.tif'}
            if file_ext not in allowed_extensions:
                return jsonify({
                    'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
                }), 400

            # Generate unique receipt ID
            receipt_id = str(uuid.uuid4())

            # Save file temporarily
            upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'receipts')
            os.makedirs(upload_dir, exist_ok=True)

            file_path = os.path.join(upload_dir, f"{receipt_id}{file_ext}")
            file.save(file_path)

            file_size = os.path.getsize(file_path)

            logger.info(f"Receipt uploaded: {receipt_id} - {original_filename} ({file_size} bytes)")

            # Store receipt metadata
            receipt_metadata = {
                'receipt_id': receipt_id,
                'original_filename': original_filename,
                'file_path': file_path,
                'file_size': file_size,
                'file_type': file_ext,
                'uploaded_at': datetime.now().isoformat(),
                'status': 'uploaded',
                'processing_status': None,
                'extracted_data': None,
                'matches': None
            }

            receipts_storage[receipt_id] = receipt_metadata

            # Auto-process if requested
            if auto_process:
                try:
                    from services import ReceiptProcessor, ReceiptMatcher

                    # Process the receipt
                    processor = ReceiptProcessor()
                    extracted_data = processor.process_receipt(file_path, original_filename)

                    receipt_metadata['extracted_data'] = extracted_data
                    receipt_metadata['processing_status'] = extracted_data.get('status', 'error')

                    # Find matching transactions if processing succeeded
                    if extracted_data.get('status') == 'success':
                        matcher = ReceiptMatcher()
                        matches = matcher.find_matches(extracted_data)

                        # Convert matches to dicts
                        matches_data = [match.to_dict() for match in matches]
                        receipt_metadata['matches'] = matches_data
                        receipt_matches_cache[receipt_id] = matches

                        logger.info(f"Receipt {receipt_id} processed: {len(matches_data)} matches found")

                    receipt_metadata['status'] = 'processed'

                except Exception as e:
                    logger.error(f"Error processing receipt {receipt_id}: {e}", exc_info=True)
                    receipt_metadata['processing_status'] = 'error'
                    receipt_metadata['processing_error'] = str(e)

            # Return response
            response = {
                'success': True,
                'receipt_id': receipt_id,
                'filename': original_filename,
                'file_size': file_size,
                'file_type': file_ext,
                'uploaded_at': receipt_metadata['uploaded_at'],
                'status': receipt_metadata['status']
            }

            if auto_process:
                response['extracted_data'] = receipt_metadata.get('extracted_data')
                response['matches'] = receipt_metadata.get('matches', [])
                response['processing_status'] = receipt_metadata.get('processing_status')

            return jsonify(response), 200

        except Exception as e:
            logger.error(f"Error uploading receipt: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/receipts/<receipt_id>/process', methods=['POST'])
    def api_process_receipt(receipt_id):
        """
        Process an uploaded receipt and find matching transactions

        URL Parameters:
            receipt_id: str - Receipt ID

        Returns:
            extracted_data: dict
            matches: list
            processing_status: str
        """
        try:
            # Get receipt from storage
            if receipt_id not in receipts_storage:
                return jsonify({'error': 'Receipt not found'}), 404

            receipt = receipts_storage[receipt_id]

            # Check if already processed
            if receipt['status'] == 'processed':
                return jsonify({
                    'success': True,
                    'message': 'Receipt already processed',
                    'extracted_data': receipt['extracted_data'],
                    'matches': receipt['matches'],
                    'processing_status': receipt['processing_status']
                }), 200

            # Process the receipt
            from services import ReceiptProcessor, ReceiptMatcher

            processor = ReceiptProcessor()
            extracted_data = processor.process_receipt(
                receipt['file_path'],
                receipt['original_filename']
            )

            receipt['extracted_data'] = extracted_data
            receipt['processing_status'] = extracted_data.get('status', 'error')

            # Find matching transactions if processing succeeded
            matches_data = []
            if extracted_data.get('status') == 'success':
                matcher = ReceiptMatcher()
                matches = matcher.find_matches(extracted_data)

                matches_data = [match.to_dict() for match in matches]
                receipt['matches'] = matches_data
                receipt_matches_cache[receipt_id] = matches

            receipt['status'] = 'processed'

            logger.info(f"Receipt {receipt_id} processed: {len(matches_data)} matches found")

            return jsonify({
                'success': True,
                'extracted_data': extracted_data,
                'matches': matches_data,
                'processing_status': receipt['processing_status']
            }), 200

        except Exception as e:
            logger.error(f"Error processing receipt {receipt_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/receipts/<receipt_id>', methods=['GET'])
    def api_get_receipt(receipt_id):
        """
        Get receipt metadata and processing results

        URL Parameters:
            receipt_id: str - Receipt ID

        Returns:
            receipt_id: str
            filename: str
            file_size: int
            file_type: str
            uploaded_at: str
            status: str
            extracted_data: dict (if processed)
            matches: list (if processed)
        """
        try:
            if receipt_id not in receipts_storage:
                return jsonify({'error': 'Receipt not found'}), 404

            receipt = receipts_storage[receipt_id]

            response = {
                'receipt_id': receipt['receipt_id'],
                'filename': receipt['original_filename'],
                'file_size': receipt['file_size'],
                'file_type': receipt['file_type'],
                'uploaded_at': receipt['uploaded_at'],
                'status': receipt['status'],
                'processing_status': receipt.get('processing_status')
            }

            if receipt['status'] == 'processed':
                response['extracted_data'] = receipt.get('extracted_data')
                response['matches'] = receipt.get('matches', [])

            return jsonify(response), 200

        except Exception as e:
            logger.error(f"Error getting receipt {receipt_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/receipts/<receipt_id>/file', methods=['GET'])
    def api_get_receipt_file(receipt_id):
        """
        Download the receipt file

        URL Parameters:
            receipt_id: str - Receipt ID

        Returns:
            File download
        """
        try:
            if receipt_id not in receipts_storage:
                return jsonify({'error': 'Receipt not found'}), 404

            receipt = receipts_storage[receipt_id]
            file_path = receipt['file_path']

            if not os.path.exists(file_path):
                return jsonify({'error': 'Receipt file not found'}), 404

            return send_file(
                file_path,
                as_attachment=True,
                download_name=receipt['original_filename']
            )

        except Exception as e:
            logger.error(f"Error downloading receipt {receipt_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/receipts/<receipt_id>/link', methods=['POST'])
    def api_link_receipt_to_transaction(receipt_id):
        """
        Link receipt to one or more transactions

        URL Parameters:
            receipt_id: str - Receipt ID

        JSON Body:
            transaction_ids: list[int] - Transaction IDs to link
            apply_categorization: bool (optional) - Apply receipt categorization suggestions (default: true)

        Returns:
            success: bool
            linked_count: int
            updated_transactions: list
        """
        try:
            if receipt_id not in receipts_storage:
                return jsonify({'error': 'Receipt not found'}), 404

            receipt = receipts_storage[receipt_id]

            # Get request data
            data = request.get_json()
            transaction_ids = data.get('transaction_ids', [])
            apply_categorization = data.get('apply_categorization', True)

            if not transaction_ids:
                return jsonify({'error': 'No transaction IDs provided'}), 400

            # Get database manager
            from database import db_manager

            linked_transactions = []

            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                for trans_id in transaction_ids:
                    # TODO: Create transaction_receipts linking table
                    # For now, we'll update the transaction with receipt metadata

                    # If apply_categorization, update transaction fields
                    if apply_categorization and receipt.get('extracted_data'):
                        extracted = receipt['extracted_data']

                        update_fields = []
                        params = []

                        # Update category if suggested
                        if extracted.get('suggested_category'):
                            update_fields.append("category = %s" if db_manager.db_type == 'postgresql' else "category = ?")
                            params.append(extracted['suggested_category'])

                        # Update entity if suggested
                        if extracted.get('suggested_business_unit'):
                            update_fields.append("entity = %s" if db_manager.db_type == 'postgresql' else "entity = ?")
                            params.append(extracted['suggested_business_unit'])

                        # Update description if available
                        if extracted.get('description') and len(update_fields) > 0:
                            # Only update if we're updating other fields
                            pass

                        if update_fields:
                            params.append(trans_id)
                            update_query = f"UPDATE transactions SET {', '.join(update_fields)} WHERE id = %s" if db_manager.db_type == 'postgresql' else f"UPDATE transactions SET {', '.join(update_fields)} WHERE id = ?"

                            cursor.execute(update_query, params)

                    linked_transactions.append({
                        'transaction_id': trans_id,
                        'receipt_id': receipt_id,
                        'linked_at': datetime.now().isoformat()
                    })

                conn.commit()

            logger.info(f"Linked receipt {receipt_id} to {len(linked_transactions)} transaction(s)")

            return jsonify({
                'success': True,
                'linked_count': len(linked_transactions),
                'linked_transactions': linked_transactions
            }), 200

        except Exception as e:
            logger.error(f"Error linking receipt {receipt_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/receipts/<receipt_id>', methods=['DELETE'])
    def api_delete_receipt(receipt_id):
        """
        Delete a receipt and its file

        URL Parameters:
            receipt_id: str - Receipt ID

        Returns:
            success: bool
            message: str
        """
        try:
            if receipt_id not in receipts_storage:
                return jsonify({'error': 'Receipt not found'}), 404

            receipt = receipts_storage[receipt_id]

            # Delete the file
            if os.path.exists(receipt['file_path']):
                os.remove(receipt['file_path'])
                logger.info(f"Deleted receipt file: {receipt['file_path']}")

            # Remove from storage
            del receipts_storage[receipt_id]

            # Remove from matches cache
            if receipt_id in receipt_matches_cache:
                del receipt_matches_cache[receipt_id]

            return jsonify({
                'success': True,
                'message': 'Receipt deleted successfully'
            }), 200

        except Exception as e:
            logger.error(f"Error deleting receipt {receipt_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/receipts', methods=['GET'])
    def api_list_receipts():
        """
        List all uploaded receipts

        Query Parameters:
            status: str (optional) - Filter by status ('uploaded', 'processed')
            limit: int (optional) - Limit number of results (default: 50)

        Returns:
            receipts: list
            total_count: int
        """
        try:
            status_filter = request.args.get('status')
            limit = int(request.args.get('limit', 50))

            receipts = list(receipts_storage.values())

            # Filter by status if specified
            if status_filter:
                receipts = [r for r in receipts if r['status'] == status_filter]

            # Sort by uploaded_at (most recent first)
            receipts.sort(key=lambda r: r['uploaded_at'], reverse=True)

            # Apply limit
            receipts = receipts[:limit]

            # Remove file_path from response (internal only)
            for receipt in receipts:
                receipt = receipt.copy()
                if 'file_path' in receipt:
                    del receipt['file_path']

            return jsonify({
                'receipts': receipts,
                'total_count': len(receipts)
            }), 200

        except Exception as e:
            logger.error(f"Error listing receipts: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/transactions/<int:transaction_id>/receipts', methods=['GET'])
    def api_get_transaction_receipts(transaction_id):
        """
        Get all receipts linked to a transaction

        URL Parameters:
            transaction_id: int - Transaction ID

        Returns:
            receipts: list
            count: int
        """
        try:
            # TODO: Query transaction_receipts linking table when implemented
            # For now, return empty list
            return jsonify({
                'receipts': [],
                'count': 0,
                'message': 'Receipt linking table not yet implemented'
            }), 200

        except Exception as e:
            logger.error(f"Error getting receipts for transaction {transaction_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    logger.info("Receipt API routes registered successfully")
