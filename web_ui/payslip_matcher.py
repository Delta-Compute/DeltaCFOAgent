#!/usr/bin/env python3
"""
Payslip Matcher - Intelligent Payslip-Transaction Matching System
Automates the identification of payslip payments through transaction analysis

Features:
- Amount matching (exact and approximate)
- Date matching (payment date vs transaction date)
- Employee name matching in transaction descriptions
- Payroll keyword detection
- Semantic matching with Claude AI
- Scoring and confidence system
- Learning from user feedback

Based on RevenueInvoiceMatcher with adaptations for payroll transactions
"""

import os
import re
import json
import logging
import concurrent.futures
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher
import anthropic
from database import db_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PayslipMatchResult:
    """Result of matching between payslip and transaction"""
    payslip_id: str
    transaction_id: str
    score: float
    match_type: str
    criteria_scores: Dict[str, float]
    confidence_level: str
    explanation: str
    auto_match: bool

class PayslipMatcher:
    """
    Main matching engine between payslips and transactions
    Adapted from RevenueInvoiceMatcher for payroll use case
    """

    def __init__(self):
        self.claude_client = self._init_claude_client()
        self.match_threshold_high = 0.80  # Automatic match threshold
        self.match_threshold_medium = 0.55  # Suggested match threshold
        self.amount_tolerance = 0.03  # 3% tolerance for amount matching

        # Progress tracking
        self.progress_lock = threading.Lock()
        self.current_progress = 0
        self.total_progress = 0
        self.start_time = None
        self.ai_filter_threshold_low = 0.4   # AI only for scores 0.4-0.8
        self.ai_filter_threshold_high = 0.8
        self.batch_size = 18  # Batch processing size
        self.max_workers = 3  # Parallel threads

        # Payroll-specific keywords for better matching
        self.payroll_keywords = [
            'salary', 'wage', 'payroll', 'compensation', 'paycheck',
            'employee payment', 'contractor payment', 'direct deposit',
            'ach payment', 'wire transfer salary', 'monthly salary',
            'biweekly pay', 'weekly pay', 'commission', 'bonus'
        ]

    def _init_claude_client(self):
        """Initialize Claude client for semantic matching"""
        try:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                return anthropic.Anthropic(api_key=api_key.strip())
            else:
                logger.warning("Claude API key not found - semantic matching disabled")
                return None
        except Exception as e:
            logger.error(f"Error initializing Claude: {e}")
            return None

    def _sanitize_text(self, text: str) -> str:
        """Sanitize text to avoid JSON errors in Claude API"""
        if not text:
            return ""
        # Remove control characters that cause JSON errors
        sanitized = text.encode('ascii', 'ignore').decode('ascii')
        # Remove line breaks that can corrupt JSON
        sanitized = sanitized.replace('\n', ' ').replace('\r', ' ')
        # Remove double quotes that can break JSON
        sanitized = sanitized.replace('"', "'")
        return sanitized.strip()

    def update_progress(self, processed: int = None):
        """Update progress thread-safe"""
        with self.progress_lock:
            if processed is not None:
                self.current_progress = processed
            else:
                self.current_progress += 1

    def get_progress_info(self) -> Dict[str, Any]:
        """Return progress information thread-safe"""
        with self.progress_lock:
            if self.total_progress == 0:
                return {"progress": 0, "eta": "N/A", "matches_processed": 0, "total": 0}

            progress_percent = (self.current_progress / self.total_progress) * 100

            if self.start_time and self.current_progress > 0:
                elapsed = time.time() - self.start_time
                rate = self.current_progress / elapsed
                remaining = (self.total_progress - self.current_progress) / rate if rate > 0 else 0
                eta = f"{int(remaining//60)}:{int(remaining%60):02d}"
            else:
                eta = "N/A"

            return {
                "progress": round(progress_percent, 1),
                "eta": eta,
                "matches_processed": self.current_progress,
                "total": self.total_progress
            }

    def find_matches_for_payslips(self, payslip_ids: List[str] = None, tenant_id: str = 'delta') -> List[PayslipMatchResult]:
        """
        Find matches for specific payslips or all unmatched payslips

        Args:
            payslip_ids: List of payslip IDs. If None, process all unmatched
            tenant_id: Tenant identifier for multi-tenant filtering

        Returns:
            List of PayslipMatchResult with found matches
        """
        logger.info(f"Starting payslip matching process for tenant {tenant_id}...")

        # Fetch unmatched payslips
        payslips = self._get_unmatched_payslips(payslip_ids, tenant_id)
        if not payslips:
            logger.info("No unmatched payslips found")
            return []

        # Fetch candidate transactions (last 6 months, NEGATIVE amounts only)
        transactions = self._get_candidate_transactions(tenant_id)
        if not transactions:
            logger.info("No candidate transactions found")
            return []

        logger.info(f"Processing {len(payslips)} payslips against {len(transactions)} transactions")

        matches = []
        for payslip in payslips:
            payslip_matches = self._find_matches_for_single_payslip(payslip, transactions)
            matches.extend(payslip_matches)

        # Sort by score descending
        matches.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"Found {len(matches)} potential matches")
        return matches

    def _get_unmatched_payslips(self, payslip_ids: List[str] = None, tenant_id: str = 'delta') -> List[Dict]:
        """Fetch payslips that haven't been matched yet"""

        # Build query with tenant filtering
        if db_manager.db_type == 'postgresql':
            query = """
                SELECT
                    p.id, p.payslip_number, p.payment_date, p.pay_period_start,
                    p.pay_period_end, p.gross_amount, p.net_amount, p.currency,
                    p.status, p.transaction_id,
                    w.full_name as employee_name, w.employment_type, w.job_title
                FROM payslips p
                JOIN workforce_members w ON p.workforce_member_id = w.id
                WHERE p.tenant_id = %s
                  AND (p.transaction_id IS NULL OR p.transaction_id = 0)
                  AND p.status IN ('approved', 'paid')
            """
        else:
            query = """
                SELECT
                    p.id, p.payslip_number, p.payment_date, p.pay_period_start,
                    p.pay_period_end, p.gross_amount, p.net_amount, p.currency,
                    p.status, p.transaction_id,
                    w.full_name as employee_name, w.employment_type, w.job_title
                FROM payslips p
                JOIN workforce_members w ON p.workforce_member_id = w.id
                WHERE p.tenant_id = ?
                  AND (p.transaction_id IS NULL OR p.transaction_id = '')
                  AND p.status IN ('approved', 'paid')
            """

        params = [tenant_id]

        if payslip_ids:
            placeholders = ', '.join(['%s' if db_manager.db_type == 'postgresql' else '?'] * len(payslip_ids))
            query += f" AND p.id IN ({placeholders})"
            params.extend(payslip_ids)

        query += " ORDER BY p.payment_date DESC"

        try:
            return db_manager.execute_query(query, tuple(params), fetch_all=True)
        except Exception as e:
            logger.error(f"Error fetching unmatched payslips: {e}")
            return []

    def _get_candidate_transactions(self, tenant_id: str = 'delta', days_back: int = None) -> List[Dict]:
        """
        Fetch candidate transactions with smart date filtering
        KEY DIFFERENCE FROM INVOICE MATCHER: Only fetches NEGATIVE transactions (outgoing payments)
        """
        # Use parameter or smart default: 6 months for payroll
        if days_back is None:
            days_back = 180  # 6 months - payroll is recent

        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        # KEY CHANGE: Filter for NEGATIVE amounts (outgoing payments)
        if db_manager.db_type == 'postgresql':
            query = """
                SELECT id as transaction_id, date, description, amount, currency,
                       entity as classified_entity, origin, destination, category, subcategory
                FROM transactions
                WHERE tenant_id = %s
                  AND amount < 0
                  AND ABS(amount) > 0.01
                  AND date >= %s
                ORDER BY date DESC
            """
        else:
            query = """
                SELECT id as transaction_id, date, description, amount, currency,
                       entity as classified_entity, origin, destination, category, subcategory
                FROM transactions
                WHERE tenant_id = ?
                  AND amount < 0
                  AND ABS(amount) > 0.01
                  AND date >= ?
                ORDER BY date DESC
            """

        try:
            transactions = db_manager.execute_query(query, (tenant_id, cutoff_date), fetch_all=True)
            logger.info(f"Found {len(transactions)} negative transactions from last {days_back} days ({cutoff_date}+)")

            # Clean and validate transactions
            valid_transactions = []
            for t in transactions:
                try:
                    # Validate amount field - convert Decimal to float safely
                    if hasattr(t['amount'], 'to_eng_string'):  # PostgreSQL Decimal
                        t['amount'] = float(t['amount'])
                    elif isinstance(t['amount'], str):
                        t['amount'] = float(t['amount'])

                    # Skip transactions with invalid amounts
                    if abs(t['amount']) > 0.01:  # Only meaningful amounts
                        valid_transactions.append(t)
                except (ValueError, TypeError, AttributeError) as e:
                    logger.warning(f"Skipping transaction {t.get('transaction_id', 'unknown')} with invalid amount: {e}")
                    continue

            logger.info(f"Valid outgoing transactions: {len(valid_transactions)}")
            return valid_transactions
        except Exception as e:
            logger.error(f"Error fetching candidate transactions: {e}")
            return []

    def _find_matches_for_single_payslip(self, payslip: Dict, transactions: List[Dict]) -> List[PayslipMatchResult]:
        """Find matches for a single payslip"""
        matches = []

        for transaction in transactions:
            match_result = self._evaluate_match(payslip, transaction)
            if match_result and match_result.score >= self.match_threshold_medium:
                matches.append(match_result)

        return matches

    def _evaluate_match(self, payslip: Dict, transaction: Dict) -> Optional[PayslipMatchResult]:
        """Evaluate if a payslip and transaction are a match"""

        # Check basic criteria
        criteria_scores = {}

        # 1. Amount matching
        amount_score = self._calculate_amount_match_score(payslip, transaction)
        criteria_scores['amount'] = amount_score

        # 2. Date matching
        date_score = self._calculate_date_match_score(payslip, transaction)
        criteria_scores['date'] = date_score

        # 3. Employee name matching in description
        employee_score = self._calculate_employee_match_score(payslip, transaction)
        criteria_scores['employee'] = employee_score

        # 4. Payroll keyword detection
        keyword_score = self._calculate_keyword_match_score(payslip, transaction)
        criteria_scores['keyword'] = keyword_score

        # 5. Pattern matching (payslip number, etc.)
        pattern_score = self._calculate_pattern_match_score(payslip, transaction)
        criteria_scores['pattern'] = pattern_score

        # Calculate weighted final score
        # For payroll, amount and employee name are most important
        final_score = (
            amount_score * 0.40 +      # Amount is critical
            date_score * 0.25 +        # Date is important
            employee_score * 0.20 +    # Employee name matching
            keyword_score * 0.10 +     # Payroll keywords
            pattern_score * 0.05       # Patterns as bonus
        )

        # Only return if minimum score reached
        if final_score < self.match_threshold_medium:
            return None

        # Determine confidence level and auto-match
        if final_score >= self.match_threshold_high:
            confidence_level = "HIGH"
            auto_match = True
        elif final_score >= self.match_threshold_medium:
            confidence_level = "MEDIUM"
            auto_match = False
        else:
            confidence_level = "LOW"
            auto_match = False

        # Generate explanation
        explanation = self._generate_match_explanation(criteria_scores, payslip, transaction)

        # Determine match type
        match_type = self._determine_match_type(criteria_scores)

        return PayslipMatchResult(
            payslip_id=payslip['id'],
            transaction_id=transaction['transaction_id'],
            score=final_score,
            match_type=match_type,
            criteria_scores=criteria_scores,
            confidence_level=confidence_level,
            explanation=explanation,
            auto_match=auto_match
        )

    def _calculate_amount_match_score(self, payslip: Dict, transaction: Dict) -> float:
        """
        Calculate amount matching score
        Compares net_amount of payslip with absolute value of transaction
        """
        try:
            payslip_amount = float(payslip['net_amount'])
            transaction_amount = abs(float(transaction['amount']))  # Use absolute value

            # Exact match
            if abs(payslip_amount - transaction_amount) < 0.01:
                return 1.0

            # Percentage difference
            diff_percentage = abs(payslip_amount - transaction_amount) / payslip_amount

            # Scoring based on tolerance
            if diff_percentage <= self.amount_tolerance:
                return 1.0 - (diff_percentage / self.amount_tolerance) * 0.1

            # Within 10% - still possible match
            if diff_percentage <= 0.10:
                return 0.80 - (diff_percentage - self.amount_tolerance) * 5

            # Within 20% - lower score
            if diff_percentage <= 0.20:
                return 0.50 - (diff_percentage - 0.10) * 2

            return 0.0

        except (ValueError, TypeError, KeyError):
            return 0.0

    def _calculate_date_match_score(self, payslip: Dict, transaction: Dict) -> float:
        """Calculate date matching score"""
        try:
            # Parse dates
            payment_date = datetime.strptime(str(payslip['payment_date']), '%Y-%m-%d').date()
            transaction_date = datetime.strptime(str(transaction['date']), '%Y-%m-%d').date()

            # Calculate difference in days
            diff_days = abs((transaction_date - payment_date).days)

            # Payroll transactions are usually on exact date or within days
            if diff_days == 0:
                return 1.0
            elif diff_days <= 2:
                return 0.95  # Same period
            elif diff_days <= 5:
                return 0.85  # Same week
            elif diff_days <= 10:
                return 0.70  # Within 10 days
            elif diff_days <= 30:
                return 0.50  # Within month
            elif diff_days <= 60:
                return 0.30  # Within 2 months
            else:
                return 0.10  # More than 2 months (unlikely)

        except (ValueError, TypeError):
            return 0.0

    def _calculate_employee_match_score(self, payslip: Dict, transaction: Dict) -> float:
        """Calculate employee name matching score in transaction description"""
        employee_name = (payslip.get('employee_name') or '').lower().strip()
        transaction_desc = (transaction.get('description') or '').lower().strip()

        if not employee_name or not transaction_desc:
            return 0.0

        # Exact match
        if employee_name in transaction_desc:
            return 1.0

        # Try matching first and last names separately
        name_parts = employee_name.split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = name_parts[-1]

            if first_name in transaction_desc and last_name in transaction_desc:
                return 0.95
            elif last_name in transaction_desc:
                return 0.80  # Last name is more unique
            elif first_name in transaction_desc:
                return 0.60

        # Fuzzy matching
        similarity = SequenceMatcher(None, employee_name, transaction_desc).ratio()
        if similarity >= 0.7:
            return similarity * 0.9

        # Try matching individual words
        name_words = set(employee_name.split())
        desc_words = set(transaction_desc.split())

        if name_words & desc_words:  # Common words
            common_ratio = len(name_words & desc_words) / len(name_words)
            return min(common_ratio * 0.7, 0.6)

        return 0.0

    def _calculate_keyword_match_score(self, payslip: Dict, transaction: Dict) -> float:
        """Calculate score based on payroll-related keywords in transaction description"""
        transaction_desc = (transaction.get('description') or '').lower().strip()
        category = (transaction.get('category') or '').lower().strip()
        subcategory = (transaction.get('subcategory') or '').lower().strip()

        if not transaction_desc:
            return 0.0

        # Check for payroll keywords
        keyword_matches = 0
        for keyword in self.payroll_keywords:
            if keyword in transaction_desc:
                keyword_matches += 1

        # Check category/subcategory
        if 'payroll' in category or 'salary' in category or 'wage' in category:
            keyword_matches += 2
        if 'payroll' in subcategory or 'salary' in subcategory or 'employee' in subcategory:
            keyword_matches += 1

        # Score based on number of matches
        if keyword_matches >= 3:
            return 1.0
        elif keyword_matches >= 2:
            return 0.8
        elif keyword_matches >= 1:
            return 0.6
        else:
            return 0.0

    def _calculate_pattern_match_score(self, payslip: Dict, transaction: Dict) -> float:
        """Calculate score based on patterns (payslip number, etc.)"""
        payslip_number = (payslip.get('payslip_number') or '').lower().strip()
        transaction_desc = (transaction.get('description') or '').lower().strip()

        if not payslip_number or not transaction_desc:
            return 0.0

        # Look for payslip number in transaction description
        if payslip_number in transaction_desc:
            return 1.0

        # Look for numeric patterns
        payslip_numbers = re.findall(r'\d+', payslip_number)
        desc_numbers = re.findall(r'\d+', transaction_desc)

        for payslip_num in payslip_numbers:
            if len(payslip_num) >= 4 and payslip_num in desc_numbers:
                return 0.8

        return 0.0

    def _determine_match_type(self, criteria_scores: Dict[str, float]) -> str:
        """Determine the primary match type based on scores"""
        max_score = max(criteria_scores.values())
        max_criterion = max(criteria_scores, key=criteria_scores.get)

        if max_criterion == 'amount' and criteria_scores['amount'] >= 0.9:
            return 'amount_exact'
        elif max_criterion == 'employee':
            return 'employee_name'
        elif max_criterion == 'amount':
            return 'amount_approximate'
        elif max_criterion == 'date':
            return 'date_proximity'
        elif max_criterion == 'keyword':
            return 'payroll_keyword'
        else:
            return 'combined'

    def _generate_match_explanation(self, criteria_scores: Dict[str, float], payslip: Dict, transaction: Dict) -> str:
        """Generate human-readable explanation of the match"""
        explanations = []

        # Amount match
        if criteria_scores.get('amount', 0) >= 0.95:
            explanations.append("Exact amount match")
        elif criteria_scores.get('amount', 0) >= 0.80:
            explanations.append("Close amount match")

        # Date match
        if criteria_scores.get('date', 0) >= 0.90:
            explanations.append("Same payment date")
        elif criteria_scores.get('date', 0) >= 0.70:
            explanations.append("Similar payment date")

        # Employee match
        if criteria_scores.get('employee', 0) >= 0.80:
            explanations.append(f"Employee name '{payslip.get('employee_name', '')}' found in description")

        # Keyword match
        if criteria_scores.get('keyword', 0) >= 0.60:
            explanations.append("Payroll-related keywords detected")

        if not explanations:
            explanations.append("Multiple weak indicators suggest potential match")

        return "; ".join(explanations)

    def save_matches_to_db(self, matches: List[PayslipMatchResult], tenant_id: str = 'delta'):
        """Save matches to pending_payslip_matches table"""
        if not matches:
            logger.info("No matches to save")
            return

        # Ensure table exists
        self._ensure_tables_exist()

        # Clear existing pending matches for these payslips
        payslip_ids = list(set([m.payslip_id for m in matches]))
        if payslip_ids:
            placeholders = ', '.join(['%s' if db_manager.db_type == 'postgresql' else '?'] * len(payslip_ids))
            delete_query = f"DELETE FROM pending_payslip_matches WHERE payslip_id IN ({placeholders})"
            db_manager.execute_query(delete_query, tuple(payslip_ids))

        # Insert new matches
        if db_manager.db_type == 'postgresql':
            insert_query = """
                INSERT INTO pending_payslip_matches
                (payslip_id, transaction_id, score, match_type, criteria_scores,
                 confidence_level, explanation, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
            """
        else:
            insert_query = """
                INSERT INTO pending_payslip_matches
                (payslip_id, transaction_id, score, match_type, criteria_scores,
                 confidence_level, explanation, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """

        for match in matches:
            try:
                db_manager.execute_query(insert_query, (
                    match.payslip_id,
                    match.transaction_id,
                    match.score,
                    match.match_type,
                    json.dumps(match.criteria_scores),
                    match.confidence_level,
                    match.explanation
                ))
            except Exception as e:
                logger.error(f"Error saving match {match.payslip_id} - {match.transaction_id}: {e}")

        logger.info(f"Saved {len(matches)} matches to database")

    def _ensure_tables_exist(self):
        """Ensure matching tables exist (should already exist from migration)"""
        # This is a safety check - tables should exist from migration
        # Implementation moved to migration script for cleaner separation
        pass


# Convenience function for external use
def run_payslip_matching(payslip_ids: List[str] = None, auto_apply: bool = False, tenant_id: str = 'delta') -> Dict[str, Any]:
    """
    Run payslip matching process

    Args:
        payslip_ids: List of specific payslip IDs to match (None = all)
        auto_apply: Whether to automatically apply high-confidence matches
        tenant_id: Tenant identifier

    Returns:
        Dictionary with matching results and statistics
    """
    matcher = PayslipMatcher()

    try:
        # Find matches
        matches = matcher.find_matches_for_payslips(payslip_ids, tenant_id)

        # Save to database
        matcher.save_matches_to_db(matches, tenant_id)

        # Calculate statistics
        high_confidence = len([m for m in matches if m.confidence_level == "HIGH"])
        medium_confidence = len([m for m in matches if m.confidence_level == "MEDIUM"])
        low_confidence = len([m for m in matches if m.confidence_level == "LOW"])

        result = {
            "success": True,
            "total_matches": len(matches),
            "high_confidence": high_confidence,
            "medium_confidence": medium_confidence,
            "low_confidence": low_confidence,
            "matches": [
                {
                    "payslip_id": m.payslip_id,
                    "transaction_id": m.transaction_id,
                    "score": round(m.score, 2),
                    "confidence": m.confidence_level,
                    "explanation": m.explanation
                }
                for m in matches[:20]  # Return top 20 for preview
            ]
        }

        logger.info(f"Matching complete: {len(matches)} matches found")
        return result

    except Exception as e:
        logger.error(f"Error in payslip matching: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_matches": 0
        }
