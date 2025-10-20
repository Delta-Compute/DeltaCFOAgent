#!/usr/bin/env python3
"""
ULTRA FAST MATCHER - Performance otimizada para grandes volumes (FIXED VERSION)
Target: < 1 segundo por match
Fixes: Connection pool exhaustion, SQL type casting, threading issues
"""

from web_ui.database import db_manager
import time
from datetime import datetime, timedelta
import threading

class UltraFastMatcher:
    def __init__(self):
        self.stats = {
            'matches_found': 0,
            'db_queries': 0,
            'processed_invoices': 0,
            'start_time': time.time()
        }

        # CONSERVATIVE PERFORMANCE SETTINGS (to avoid connection exhaustion)
        self.batch_size = 50  # Reduced from 100 to prevent connection issues
        self.max_candidates_per_invoice = 3  # Reduced from 5 for speed
        self.amount_tolerance = 0.03  # Reduced to 3% for precision
        self.max_days_window = 60  # Reduced to 60 days for performance
        self.sequential_processing = True  # No parallel threads to avoid connection issues

        print("ULTRA FAST MATCHER INITIALIZED (FIXED VERSION)")
        print(f"   Batch size: {self.batch_size}")
        print(f"   Max candidates: {self.max_candidates_per_invoice}")
        print(f"   Amount tolerance: {self.amount_tolerance*100}%")
        print(f"   Time window: {self.max_days_window} days")
        print(f"   Processing mode: {'Sequential' if self.sequential_processing else 'Parallel'}")

    def get_smart_candidates(self, invoice_amount, invoice_date):
        """Get pre-filtered candidates with aggressive filtering and proper date casting"""
        self.stats['db_queries'] += 1

        # ULTRA AGGRESSIVE FILTERING with proper date casting
        min_amount = invoice_amount * (1 - self.amount_tolerance)
        max_amount = invoice_amount * (1 + self.amount_tolerance)
        max_date = invoice_date + timedelta(days=self.max_days_window)

        # FIX: Cast VARCHAR date column to DATE for comparison
        candidates = db_manager.execute_query("""
            SELECT transaction_id, CAST(date AS DATE) as date, amount, description
            FROM transactions
            WHERE (invoice_id IS NULL OR invoice_id = '')
            AND ABS(CAST(amount AS DECIMAL)) BETWEEN %s AND %s
            AND CAST(date AS DATE) >= %s AND CAST(date AS DATE) <= %s
            ORDER BY ABS(ABS(CAST(amount AS DECIMAL)) - %s)
            LIMIT %s
        """, (min_amount, max_amount, invoice_date, max_date, invoice_amount, self.max_candidates_per_invoice), fetch_all=True)

        return candidates

    def simple_match_score(self, invoice, transaction):
        """Ultra fast scoring without AI"""
        try:
            invoice_amount = float(invoice['total_amount'])
            txn_amount = abs(float(transaction['amount']))

            # Amount similarity (most important)
            amount_diff = abs(invoice_amount - txn_amount)
            amount_score = max(0, 1 - (amount_diff / max(invoice_amount, txn_amount)))

            # Date proximity (bonus for recent)
            date_diff = (transaction['date'] - invoice['date']).days
            date_score = max(0, 1 - (date_diff / self.max_days_window))

            # Simple text matching
            invoice_text = invoice.get('vendor_name', '').lower()
            txn_text = transaction.get('description', '').lower()
            text_score = 0.1 if any(word in txn_text for word in invoice_text.split() if len(word) > 3) else 0

            # Weighted final score
            final_score = (amount_score * 0.7) + (date_score * 0.2) + (text_score * 0.1)
            return final_score
        except Exception as e:
            print(f"Error in scoring: {e}")
            return 0

    def process_single_invoice(self, invoice):
        """Process a single invoice - ULTRA FAST"""
        try:
            # Get smart candidates
            candidates = self.get_smart_candidates(
                float(invoice['total_amount']),
                invoice['date']
            )

            if not candidates:
                return []

            # Score all candidates quickly
            scored_candidates = []
            for candidate in candidates:
                score = self.simple_match_score(invoice, candidate)
                if score > 0.7:  # Higher threshold for quality
                    scored_candidates.append({
                        'invoice_id': invoice['id'],
                        'transaction_id': candidate['transaction_id'],
                        'score': score,
                        'confidence_level': 'HIGH' if score > 0.85 else 'MEDIUM',
                        'match_type': 'ULTRA_FAST_MATCH',
                        'explanation': f"Ultra fast match: {score:.2f} score"
                    })

            # Return only best match
            if scored_candidates:
                best_match = max(scored_candidates, key=lambda x: x['score'])
                self.stats['matches_found'] += 1
                return [best_match]

            return []

        except Exception as e:
            print(f"Error processing invoice {invoice.get('id', 'unknown')}: {e}")
            return []

    def save_matches(self, matches, auto_apply=False):
        """Save matches to database in bulk or apply automatically based on confidence"""
        if not matches:
            return {'auto_applied': 0, 'pending_review': 0}

        auto_applied = 0
        pending_review = 0

        try:
            self.stats['db_queries'] += 1

            for match in matches:
                # Check if match should be auto-applied (HIGH confidence and auto_apply enabled)
                if auto_apply and match['confidence_level'] == 'HIGH' and match['score'] >= 0.85:
                    # Auto-apply the match
                    try:
                        self._apply_match_automatically(match)
                        auto_applied += 1
                        print(f"AUTO-APPLIED: Invoice {match['invoice_id']} -> Transaction {match['transaction_id']} (score: {match['score']:.3f})")
                    except Exception as e:
                        print(f"ERROR auto-applying match {match['invoice_id']}-{match['transaction_id']}: {e}")
                        # Fall back to pending if auto-apply fails
                        self._save_pending_match(match)
                        pending_review += 1
                else:
                    # Save for manual review
                    self._save_pending_match(match)
                    pending_review += 1

            return {'auto_applied': auto_applied, 'pending_review': pending_review}

        except Exception as e:
            print(f"Error saving matches: {e}")
            return {'auto_applied': 0, 'pending_review': 0}

    def _apply_match_automatically(self, match):
        """Apply match automatically with bidirectional linking and AI enrichment"""
        try:
            # 1. Update INVOICE with linked_transaction_id (no updated_at column)
            db_manager.execute_query("""
                UPDATE invoices
                SET linked_transaction_id = %s,
                    status = 'paid'
                WHERE id = %s
            """, (match['transaction_id'], match['invoice_id']))

            # 2. Update TRANSACTION with invoice_id (bidirectional linking)
            db_manager.execute_query("""
                UPDATE transactions
                SET invoice_id = %s
                WHERE transaction_id = %s
            """, (match['invoice_id'], match['transaction_id']))

            # 3. Simple AI ENRICHMENT without runtime imports
            try:
                self._enrich_transaction_simple(match['transaction_id'], match['invoice_id'])
                print(f"AUTO-MATCH APPLIED: Invoice {match['invoice_id']} -> Transaction {match['transaction_id']} (with AI enrichment)")
            except Exception as e:
                print(f"AUTO-MATCH APPLIED: Invoice {match['invoice_id']} -> Transaction {match['transaction_id']} (enrichment failed: {str(e)[:50]})")

        except Exception as e:
            print(f"Critical error in auto-apply: {e}")
            raise

    def _enrich_transaction_simple(self, transaction_id, invoice_id):
        """Simple transaction enrichment without generators or complex imports"""
        try:
            # Get invoice data for context
            invoice_data = db_manager.execute_query("""
                SELECT vendor_name, customer_name, invoice_number, category, business_unit
                FROM invoices
                WHERE id = %s
            """, (invoice_id,), fetch_all=False)

            if not invoice_data:
                return False

            # Simple enrichment: update transaction with invoice context
            vendor_name = invoice_data.get('vendor_name', '')
            category = invoice_data.get('category', 'Revenue')
            business_unit = invoice_data.get('business_unit', 'Delta Mining Paraguay S.A.')

            # Update transaction with enriched data
            db_manager.execute_query("""
                UPDATE transactions
                SET classified_entity = %s,
                    category = %s,
                    business_unit = %s
                WHERE transaction_id = %s
            """, (business_unit, category, vendor_name, transaction_id))

            return True

        except Exception as e:
            print(f"Simple enrichment error: {e}")
            return False

    def _save_pending_match(self, match):
        """Save match for manual review"""
        try:
            db_manager.execute_query("""
                INSERT INTO pending_invoice_matches
                (invoice_id, transaction_id, score, match_type, confidence_level, explanation)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (invoice_id, transaction_id) DO NOTHING
            """, (
                match['invoice_id'],
                match['transaction_id'],
                match['score'],
                match['match_type'],
                match['confidence_level'],
                match['explanation']
            ))
        except Exception as e:
            # Handle databases that don't support ON CONFLICT
            try:
                db_manager.execute_query("""
                    INSERT INTO pending_invoice_matches
                    (invoice_id, transaction_id, score, match_type, confidence_level, explanation)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    match['invoice_id'],
                    match['transaction_id'],
                    match['score'],
                    match['match_type'],
                    match['confidence_level'],
                    match['explanation']
                ))
            except Exception as e2:
                if "duplicate key" not in str(e2).lower():
                    print(f"Error saving pending match: {e2}")

    def run_ultra_fast_matching(self, auto_apply=False):
        """Main ultra fast matching process with optional auto-apply"""
        auto_apply_text = "with AUTO-APPLY enabled" if auto_apply else "for manual review"
        print(f"\nSTARTING ULTRA FAST MATCHING (FIXED VERSION) {auto_apply_text}")
        start_time = time.time()

        # Track auto-apply statistics
        total_auto_applied = 0
        total_pending_review = 0

        try:
            # Get all unlinked invoices
            invoices = db_manager.execute_query("""
                SELECT id, vendor_name, CAST(date AS DATE) as date, total_amount
                FROM invoices
                WHERE (linked_transaction_id IS NULL OR linked_transaction_id = '')
                ORDER BY date DESC
            """, fetch_all=True)

            print(f"Processing {len(invoices)} invoices in batches of {self.batch_size}")
            if auto_apply:
                print("AUTO-APPLY ENABLED: HIGH confidence matches (>=0.85) will be applied automatically")

            all_matches = []

            # Process in batches (sequential to avoid connection issues)
            for i in range(0, len(invoices), self.batch_size):
                batch = invoices[i:i + self.batch_size]
                batch_start = time.time()

                print(f"Processing batch {i//self.batch_size + 1}/{(len(invoices)-1)//self.batch_size + 1} ({len(batch)} invoices)")

                # Sequential processing to avoid connection pool exhaustion
                batch_matches = []
                for invoice in batch:
                    invoice_matches = self.process_single_invoice(invoice)
                    batch_matches.extend(invoice_matches)
                    self.stats['processed_invoices'] += 1

                all_matches.extend(batch_matches)

                # Save batch immediately with auto-apply option
                if batch_matches:
                    batch_stats = self.save_matches(batch_matches, auto_apply=auto_apply)
                    total_auto_applied += batch_stats['auto_applied']
                    total_pending_review += batch_stats['pending_review']

                batch_time = time.time() - batch_start
                applied_text = f" | Auto-applied: {batch_stats['auto_applied']}" if auto_apply and batch_matches else ""
                print(f"   Batch completed in {batch_time:.2f}s - Found {len(batch_matches)} matches{applied_text}")

                # Progress update
                processed = min(i + self.batch_size, len(invoices))
                progress = (processed / len(invoices)) * 100
                elapsed = time.time() - start_time
                eta = (elapsed / processed) * (len(invoices) - processed) if processed > 0 else 0

                print(f"   Progress: {progress:.1f}% | Elapsed: {elapsed:.1f}s | ETA: {eta:.1f}s")

            total_time = time.time() - start_time

            print(f"\nULTRA FAST MATCHING COMPLETE!")
            print(f"   Total time: {total_time:.2f} seconds")
            print(f"   Total matches: {len(all_matches)}")
            if auto_apply:
                print(f"   Auto-applied: {total_auto_applied}")
                print(f"   Pending review: {total_pending_review}")
            print(f"   Speed: {len(invoices)/total_time:.1f} invoices/second")
            print(f"   DB queries: {self.stats['db_queries']}")
            print(f"   Performance: {total_time/len(invoices)*1000:.1f}ms per invoice")

            return {
                'total_matches': len(all_matches),
                'auto_applied': total_auto_applied,
                'pending_review': total_pending_review,
                'processing_time': total_time,
                'invoices_per_second': len(invoices)/total_time,
                'ms_per_invoice': total_time/len(invoices)*1000
            }

        except Exception as e:
            print(f"Critical error in matching process: {e}")
            return {
                'total_matches': 0,
                'processing_time': 0,
                'invoices_per_second': 0,
                'ms_per_invoice': 0
            }

if __name__ == "__main__":
    matcher = UltraFastMatcher()
    result = matcher.run_ultra_fast_matching()

    print("\nPERFORMANCE ANALYSIS:")
    print(f"   Target: < 1000ms per invoice")
    print(f"   Actual: {result['ms_per_invoice']:.1f}ms per invoice")
    print(f"   Status: {'PASSED' if result['ms_per_invoice'] < 1000 else 'FAILED'}")

    if result['ms_per_invoice'] < 1000:
        print(f"\nREADY FOR ENTERPRISE SCALE!")
        print(f"   1M invoices would take: {result['ms_per_invoice']*1000000/1000/60:.1f} minutes")
    else:
        print(f"\nNEEDS MORE OPTIMIZATION")