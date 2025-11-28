"""
Pattern Learning Module - LLM-Validated 3-Occurrence System

This module implements intelligent pattern learning with:
- Similarity detection (description + origin/destination)
- LLM validation using tenant context
- Automated pattern creation
- Passive notifications

Author: DeltaCFO AI Team
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import asyncio

from database import db_manager

logger = logging.getLogger(__name__)


# ============================================================================
# PATTERN SUGGESTION PROCESSING
# ============================================================================

async def process_pending_pattern_suggestions(tenant_id: str, claude_client) -> int:
    """
    Process all pending pattern suggestions for a tenant.

    This function is called periodically (or triggered after new tracking records)
    to validate pending patterns with LLM and auto-create them if validated.

    Returns:
        int: Number of patterns processed
    """
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Get all pending pattern suggestions
            cursor.execute("""
                SELECT id, tenant_id, description_pattern, pattern_type, entity,
                       accounting_category, accounting_subcategory, justification,
                       occurrence_count, confidence_score, supporting_classifications
                FROM pattern_suggestions
                WHERE tenant_id = %s
                  AND status = 'pending'
                  AND llm_validation_result IS NULL
                ORDER BY occurrence_count DESC, created_at DESC
                LIMIT 10
            """, (tenant_id,))

            suggestions = cursor.fetchall()

            if not suggestions:
                logger.info(f"No pending pattern suggestions for tenant {tenant_id}")
                cursor.close()
                return 0

            logger.info(f"Processing {len(suggestions)} pending pattern suggestions for tenant {tenant_id}")

            processed_count = 0

            for suggestion in suggestions:
                suggestion_id = suggestion[0]
                pattern_data = {
                    'description_pattern': suggestion[2],
                    'pattern_type': suggestion[3],
                    'entity': suggestion[4],
                    'accounting_category': suggestion[5],
                    'accounting_subcategory': suggestion[6],
                    'justification': suggestion[7],
                    'occurrence_count': suggestion[8],
                    'confidence_score': float(suggestion[9]),
                    'supporting_classifications': suggestion[10]
                }

                # Get supporting transactions for context
                supporting_txns = await get_supporting_transactions(
                    cursor,
                    pattern_data['supporting_classifications']
                )

                # Calculate pattern statistics for enriched validation
                pattern_stats = calculate_pattern_statistics(supporting_txns)

                # Validate with LLM (two-pass system)
                validation_result = await validate_pattern_with_llm(
                    tenant_id=tenant_id,
                    pattern_data=pattern_data,
                    supporting_transactions=supporting_txns,
                    pattern_stats=pattern_stats,
                    claude_client=claude_client
                )

                # Update pattern_suggestions with validation result
                cursor.execute("""
                    UPDATE pattern_suggestions
                    SET llm_validation_result = %s,
                        llm_validated_at = CURRENT_TIMESTAMP,
                        validation_model = %s,
                        status = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    json.dumps(validation_result),
                    validation_result.get('model_used', 'claude-sonnet-4-5-20250929'),
                    'approved' if validation_result['is_valid'] else 'rejected',
                    suggestion_id
                ))

                conn.commit()

                # If validated, create classification pattern
                if validation_result['is_valid']:
                    pattern_id = await create_llm_validated_pattern(
                        cursor=cursor,
                        conn=conn,
                        tenant_id=tenant_id,
                        pattern_data=pattern_data,
                        validation_result=validation_result,
                        suggestion_id=suggestion_id
                    )

                    if pattern_id:
                        # Create passive notification
                        await create_pattern_notification(
                            cursor=cursor,
                            conn=conn,
                            tenant_id=tenant_id,
                            pattern_id=pattern_id,
                            notification_type='pattern_created',
                            pattern_data=pattern_data,
                            validation_result=validation_result
                        )

                        logger.info(f"✅ Created LLM-validated pattern #{pattern_id} for tenant {tenant_id}")
                        processed_count += 1
                else:
                    logger.info(f"❌ LLM rejected pattern suggestion #{suggestion_id}: {validation_result.get('reasoning')}")

            cursor.close()
            return processed_count

    except Exception as e:
        logger.error(f"Error processing pattern suggestions: {e}", exc_info=True)
        return 0


# ============================================================================
# LLM VALIDATION
# ============================================================================

async def validate_pattern_with_llm(
    tenant_id: str,
    pattern_data: Dict,
    supporting_transactions: List[Dict],
    pattern_stats: Dict,
    claude_client
) -> Dict:
    """
    Validate a pattern suggestion with Claude LLM using two-pass validation.

    PASS 1: Basic validation with pattern and business context
    PASS 2: If rejected, retry with enriched temporal/amount statistics

    Uses tenant's business context to assess pattern quality.

    Returns:
        {
            'is_valid': bool,
            'confidence_adjustment': float,
            'reasoning': str,
            'suggested_improvements': dict,
            'risk_assessment': str,
            'model_used': str,
            'pass_number': int  # 1 or 2
        }
    """
    try:
        # Load tenant context
        tenant_context = await load_tenant_context(tenant_id)

        # PASS 1: Basic validation
        logger.info(f"🤖 Pass 1: Basic pattern validation for tenant {tenant_id}")

        prompt_pass1 = build_validation_prompt(
            tenant_context=tenant_context,
            pattern_data=pattern_data,
            supporting_transactions=supporting_transactions,
            pattern_stats=None,  # Don't include stats in first pass
            previous_rejection=None
        )

        response = claude_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.3,
            messages=[{
                "role": "user",
                "content": prompt_pass1
            }]
        )

        validation_result = parse_validation_response(response.content[0].text)
        validation_result['model_used'] = 'claude-sonnet-4-5-20250929'
        validation_result['pass_number'] = 1

        logger.info(f"✅ Pass 1 complete: {validation_result.get('is_valid')}")

        # If approved, we're done
        if validation_result['is_valid']:
            return validation_result

        # PASS 2: Enriched validation with temporal/amount statistics
        # Check if this is a recurring pattern worth reconsidering
        if pattern_stats.get('is_recurring') or pattern_data.get('occurrence_count', 0) >= 15:
            logger.info(f"🔄 Pass 2: Enriched validation with temporal/amount statistics")
            logger.info(f"   Stats: frequency={pattern_stats.get('temporal_frequency')}, "
                       f"variance={pattern_stats.get('amount_variance')}, "
                       f"recurring={pattern_stats.get('is_recurring')}")

            prompt_pass2 = build_validation_prompt(
                tenant_context=tenant_context,
                pattern_data=pattern_data,
                supporting_transactions=supporting_transactions,
                pattern_stats=pattern_stats,
                previous_rejection=validation_result.get('reasoning')
            )

            response_pass2 = claude_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt_pass2
                }]
            )

            validation_result_pass2 = parse_validation_response(response_pass2.content[0].text)
            validation_result_pass2['model_used'] = 'claude-sonnet-4-5-20250929'
            validation_result_pass2['pass_number'] = 2

            logger.info(f"✅ Pass 2 complete: {validation_result_pass2.get('is_valid')}")

            return validation_result_pass2
        else:
            logger.info(f"⏭️ Skipping Pass 2: Not a recurring pattern (frequency={pattern_stats.get('temporal_frequency')}, count={pattern_data.get('occurrence_count')})")
            return validation_result

    except Exception as e:
        logger.error(f"Error in LLM validation: {e}", exc_info=True)
        return {
            'is_valid': False,
            'confidence_adjustment': 0.0,
            'reasoning': f'LLM validation failed: {str(e)}',
            'suggested_improvements': {},
            'risk_assessment': 'high',
            'model_used': 'error',
            'pass_number': 0
        }


def parse_validation_response(response_text: str) -> Dict:
    """Parse Claude's validation response from text"""
    try:
        # Extract JSON from response (handle markdown code blocks)
        if '```json' in response_text:
            json_str = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            json_str = response_text.split('```')[1].split('```')[0].strip()
        else:
            json_str = response_text

        return json.loads(json_str)

    except Exception as e:
        logger.error(f"Failed to parse validation response: {e}")
        # Return safe default
        return {
            'is_valid': False,
            'confidence_adjustment': 0.0,
            'reasoning': f'Failed to parse LLM response: {str(e)}',
            'suggested_improvements': {},
            'risk_assessment': 'high'
        }


def build_validation_prompt(
    tenant_context: Dict,
    pattern_data: Dict,
    supporting_transactions: List[Dict],
    pattern_stats: Optional[Dict] = None,
    previous_rejection: Optional[str] = None
) -> str:
    """Build the prompt for LLM validation (supports two-pass validation)"""

    # Format supporting transactions
    txn_examples = ""
    for i, txn in enumerate(supporting_transactions[:5], 1):  # Show max 5 examples
        txn_examples += f"""
Transaction {i}:
  - Date: {txn.get('date', 'N/A')}
  - Description: {txn.get('description', 'N/A')}
  - Origin: {txn.get('origin', 'N/A')}
  - Destination: {txn.get('destination', 'N/A')}
  - Amount: {txn.get('amount', 'N/A')}
  - User classified as: {txn.get('user_classification', 'N/A')}
"""

    # Format existing patterns summary
    existing_patterns_summary = "\n".join([
        f"  - {p['pattern']} → {p['entity']} ({p['category']})"
        for p in tenant_context.get('existing_patterns', [])[:10]
    ])

    # Build enriched context for Pass 2
    enrichment_section = ""
    if pattern_stats:
        enrichment_section = f"""

🔍 TEMPORAL & AMOUNT ANALYSIS (ENRICHED CONTEXT):

This pattern appears to be RECURRING based on statistical analysis:

Temporal Pattern:
  - Frequency: {pattern_stats.get('temporal_frequency')} transactions
  - Time span: {pattern_stats.get('time_span_days')} days
  - Is recurring: {'YES' if pattern_stats.get('is_recurring') else 'NO'}

Amount Consistency:
  - Mean amount: ${pattern_stats.get('amount_mean', 0):.2f}
  - Range: ${pattern_stats.get('amount_min', 0):.2f} - ${pattern_stats.get('amount_max', 0):.2f}
  - Variance: {pattern_stats.get('amount_variance', 0):.1%} (lower = more consistent)

User Behavior Signal:
  - The user has classified this same type of transaction {pattern_data.get('occurrence_count', 0)} times
  - This demonstrates clear user intent and pattern recognition
  - Repetitive manual classification suggests this is a legitimate business pattern

PREVIOUS REJECTION REASON:
{previous_rejection}

RECONSIDERATION GUIDANCE:
When a pattern shows strong temporal consistency (daily/weekly/monthly) AND amount consistency (<15% variance) AND high occurrence count (15+), it indicates a legitimate recurring business transaction that the user recognizes. Even if the description pattern syntax is imperfect, the USER'S REPEATED CLASSIFICATION is a strong signal that this pattern should be approved to save them time.

Consider approving if:
1. Temporal frequency is consistent (daily/weekly/monthly)
2. Amount variance is low (<20%)
3. User has classified it many times (10+)
4. The business context makes sense (e.g., mining company receiving daily Bitcoin)
"""

    prompt = f"""ROLE: You are a financial pattern validation expert{' performing SECOND-PASS validation with enriched context' if pattern_stats else ''}.

TENANT BUSINESS CONTEXT:
- Company: {tenant_context.get('company_name', 'Unknown')}
- Industry: {tenant_context.get('industry', 'Not specified')}
- Description: {tenant_context.get('description', 'Not provided')}

Known Business Entities ({len(tenant_context.get('entities', []))} total):
{', '.join(tenant_context.get('entities', [])[:20])}

Existing Classification Patterns ({len(tenant_context.get('existing_patterns', []))} total):
{existing_patterns_summary}

PROPOSED PATTERN:
- Description pattern: "{pattern_data.get('description_pattern', 'N/A')}"
- Suggested entity: "{pattern_data.get('entity', 'N/A')}"
- Suggested category: "{pattern_data.get('accounting_category', 'N/A')}"
- Suggested subcategory: "{pattern_data.get('subcategory', 'N/A')}"
- Current confidence: {pattern_data.get('confidence_score', 0.0):.2f}
- Occurrence count: {pattern_data.get('occurrence_count', 0)}

SUPPORTING EVIDENCE ({len(supporting_transactions)} similar transactions):
{txn_examples}
{enrichment_section}

VALIDATION TASK:
Analyze whether this pattern is:
1. ACCURATE - Does it correctly identify these transaction types?
2. USEFUL - Will it help classify future similar transactions?
3. SAFE - Low risk of misclassifying unrelated transactions?
4. SPECIFIC ENOUGH - Won't match too broadly?
5. CONSISTENT - Makes sense for this company's business?

IMPORTANT CONSIDERATIONS:
- If the pattern is too generic (like "%payment%" or "%fee%"), it may cause false positives
- If origin/destination is very specific (like "stripe.com"), the pattern is safer
- If the entity already exists in the system, that's a good sign
- If similar patterns exist, check for conflicts
- Consider if the pattern might match transactions from different vendors/categories
{' - **CRITICAL FOR PASS 2**: User behavior (high occurrence count + temporal consistency) is a STRONG positive signal' if pattern_stats else ''}

Respond in JSON format:
{{
  "is_valid": boolean,
  "confidence_adjustment": float (-0.2 to +0.2),
  "reasoning": "Brief explanation of your decision (2-3 sentences)",
  "suggested_improvements": {{
    "description_pattern": "refined pattern if needed (or null)",
    "entity": "refined entity if needed (or null)",
    "justification": "suggested justification text (or null)"
  }},
  "risk_assessment": "low|medium|high"
}}

Focus on {'user behavior patterns and recurring transactions' if pattern_stats else 'safety and accuracy. When in doubt, err on the side of caution'}."""

    return prompt


async def load_tenant_context(tenant_id: str) -> Dict:
    """
    Load tenant's business context for LLM validation.

    Returns:
        {
            'company_name': str,
            'industry': str,
            'description': str,
            'entities': List[str],
            'existing_patterns': List[dict]
        }

    Raises:
        Exception: If unable to load tenant context from database
    """
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        # Get tenant configuration
        cursor.execute("""
            SELECT company_name, industry, description
            FROM tenant_configuration
            WHERE tenant_id = %s
        """, (tenant_id,))

        tenant_row = cursor.fetchone()

        if not tenant_row:
            raise ValueError(f"No tenant configuration found for tenant_id: {tenant_id}")

        context = {
            'company_name': tenant_row[0] or 'Not provided',
            'industry': tenant_row[1] or 'Not specified',
            'description': tenant_row[2] or 'Not provided'
        }

        # Get business entities
        cursor.execute("""
            SELECT name
            FROM business_entities
            WHERE tenant_id = %s AND active = TRUE
            ORDER BY name
        """, (tenant_id,))

        context['entities'] = [row[0] for row in cursor.fetchall()]

        # Get existing classification patterns (summary)
        cursor.execute("""
            SELECT description_pattern, entity, accounting_category
            FROM classification_patterns
            WHERE tenant_id = %s
            ORDER BY created_at DESC
            LIMIT 50
        """, (tenant_id,))

        context['existing_patterns'] = [
            {
                'pattern': row[0],
                'entity': row[1],
                'category': row[2]
            }
            for row in cursor.fetchall()
        ]

        cursor.close()

        logger.info(f"Loaded tenant context: {context['company_name']} with {len(context['entities'])} entities and {len(context['existing_patterns'])} patterns")

        return context


async def get_supporting_transactions(cursor, supporting_classifications_json) -> List[Dict]:
    """
    Retrieve the actual transactions that support this pattern.

    Args:
        cursor: Database cursor
        supporting_classifications_json: JSONB array of tracking IDs

    Returns:
        List of transaction dictionaries
    """
    try:
        if not supporting_classifications_json:
            return []

        # Parse the JSONB
        if isinstance(supporting_classifications_json, str):
            tracking_records = json.loads(supporting_classifications_json)
        else:
            tracking_records = supporting_classifications_json

        # Extract tracking IDs - handle both formats:
        # 1. Array of integers: [1, 2, 3]
        # 2. Array of objects: [{"id": 1}, {"id": 2}]
        if not tracking_records:
            return []

        if isinstance(tracking_records[0], int):
            # Direct array of integers
            tracking_ids = tracking_records
        else:
            # Array of objects with 'id' field
            tracking_ids = [record['id'] for record in tracking_records if 'id' in record]

        if not tracking_ids:
            return []

        # Get transactions - ORDER BY date for temporal analysis
        placeholders = ','.join(['%s'] * len(tracking_ids))
        cursor.execute(f"""
            SELECT
                t.transaction_id,
                t.date,
                t.description,
                t.origin,
                t.destination,
                t.amount,
                t.currency,
                uct.new_value as user_classification,
                uct.field_changed,
                uct.created_at
            FROM user_classification_tracking uct
            JOIN transactions t ON uct.transaction_id = t.transaction_id
            WHERE uct.id IN ({placeholders})
            ORDER BY t.date ASC
        """, tuple(tracking_ids))

        transactions = []
        for row in cursor.fetchall():
            transactions.append({
                'transaction_id': str(row[0]),
                'date': str(row[1]),
                'description': row[2],
                'origin': row[3],
                'destination': row[4],
                'amount': float(row[5]) if row[5] else 0,
                'currency': row[6],
                'user_classification': row[7],
                'field_changed': row[8],
                'classified_at': str(row[9])
            })

        return transactions

    except Exception as e:
        logger.error(f"Error getting supporting transactions: {e}", exc_info=True)
        return []


def calculate_pattern_statistics(transactions: List[Dict]) -> Dict:
    """
    Calculate temporal and amount statistics for pattern validation.

    Returns:
        {
            'temporal_frequency': str,  # 'daily', 'weekly', 'monthly', 'irregular'
            'amount_variance': float,  # coefficient of variation (0-1, lower is more consistent)
            'amount_min': float,
            'amount_max': float,
            'amount_mean': float,
            'time_span_days': int,
            'is_recurring': bool
        }
    """
    from datetime import datetime
    import statistics

    if not transactions or len(transactions) < 2:
        return {
            'temporal_frequency': 'insufficient_data',
            'amount_variance': 0.0,
            'amount_min': 0.0,
            'amount_max': 0.0,
            'amount_mean': 0.0,
            'time_span_days': 0,
            'is_recurring': False
        }

    # Parse dates
    dates = []
    amounts = []

    for txn in transactions:
        try:
            # Handle both date-only and datetime formats
            date_str = txn['date']
            if 'T' in date_str or ' ' in date_str:
                # Has time component
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                # Date only
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            dates.append(date_obj)
            amounts.append(abs(txn['amount']))  # Use absolute values
        except Exception as e:
            logger.warning(f"Failed to parse date {txn.get('date')}: {e}")
            continue

    if len(dates) < 2 or len(amounts) < 2:
        return {
            'temporal_frequency': 'insufficient_data',
            'amount_variance': 0.0,
            'amount_min': 0.0,
            'amount_max': 0.0,
            'amount_mean': 0.0,
            'time_span_days': 0,
            'is_recurring': False
        }

    # Sort by date
    dates.sort()

    # Calculate time span
    time_span = (dates[-1] - dates[0]).days

    # Calculate intervals between consecutive transactions
    intervals = []
    for i in range(1, len(dates)):
        interval_days = (dates[i] - dates[i-1]).days
        if interval_days > 0:  # Ignore same-day duplicates
            intervals.append(interval_days)

    # Determine temporal frequency
    if not intervals:
        frequency = 'insufficient_data'
    else:
        avg_interval = statistics.mean(intervals)
        interval_variance = statistics.stdev(intervals) if len(intervals) > 1 else 0

        if avg_interval <= 2 and interval_variance <= 2:
            frequency = 'daily'
        elif avg_interval <= 8 and interval_variance <= 3:
            frequency = 'weekly'
        elif avg_interval <= 35 and interval_variance <= 7:
            frequency = 'monthly'
        else:
            frequency = 'irregular'

    # Calculate amount statistics
    amount_min = min(amounts)
    amount_max = max(amounts)
    amount_mean = statistics.mean(amounts)

    # Coefficient of variation (CV) - measures amount consistency
    # CV = std_dev / mean (lower = more consistent)
    amount_std = statistics.stdev(amounts) if len(amounts) > 1 else 0
    amount_variance = (amount_std / amount_mean) if amount_mean > 0 else 0

    # Determine if recurring
    is_recurring = (
        frequency in ['daily', 'weekly', 'monthly'] and
        amount_variance < 0.15  # Less than 15% variation in amounts
    )

    return {
        'temporal_frequency': frequency,
        'amount_variance': round(amount_variance, 3),
        'amount_min': round(amount_min, 2),
        'amount_max': round(amount_max, 2),
        'amount_mean': round(amount_mean, 2),
        'time_span_days': time_span,
        'is_recurring': is_recurring
    }


# ============================================================================
# PATTERN CREATION
# ============================================================================

async def create_llm_validated_pattern(
    cursor,
    conn,
    tenant_id: str,
    pattern_data: Dict,
    validation_result: Dict,
    suggestion_id: int
) -> Optional[int]:
    """
    Create a classification pattern after LLM validation.

    Returns:
        int: Pattern ID if successful, None otherwise
    """
    try:
        logger.info(f"[PATTERN_CREATION] Starting for suggestion #{suggestion_id}, tenant={tenant_id}")
        # Apply LLM suggested improvements
        description_pattern = validation_result.get('suggested_improvements', {}).get('description_pattern') or pattern_data['description_pattern']
        entity = validation_result.get('suggested_improvements', {}).get('entity') or pattern_data['entity']
        justification = validation_result.get('suggested_improvements', {}).get('justification') or pattern_data.get('justification')

        # Calculate final confidence
        base_confidence = pattern_data['confidence_score']
        llm_adjustment = validation_result.get('confidence_adjustment', 0.0)
        final_confidence = max(0.4, min(0.95, base_confidence + llm_adjustment))

        # Get risk assessment
        risk = validation_result.get('risk_assessment', 'medium')

        # Insert into classification_patterns
        cursor.execute("""
            INSERT INTO classification_patterns (
                tenant_id, description_pattern, pattern_type, entity,
                accounting_category, accounting_subcategory, justification,
                confidence_score, created_by,
                llm_confidence_adjustment, risk_assessment
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING pattern_id
        """, (
            tenant_id,
            description_pattern,
            pattern_data.get('pattern_type', 'expense'),
            entity,
            pattern_data.get('accounting_category'),
            pattern_data.get('accounting_subcategory'),
            f"Auto-created from suggestion #{suggestion_id}. {validation_result.get('reasoning', '')}",
            final_confidence,
            'llm_validated',
            llm_adjustment,
            risk
        ))

        pattern_id = cursor.fetchone()[0]
        conn.commit()

        logger.info(f"✅ Created classification pattern #{pattern_id} (confidence: {final_confidence:.2f}, risk: {risk})")

        return pattern_id

    except Exception as e:
        logger.error(f"Error creating LLM-validated pattern: {e}", exc_info=True)
        conn.rollback()
        return None


# ============================================================================
# NOTIFICATIONS
# ============================================================================

async def create_pattern_notification(
    cursor,
    conn,
    tenant_id: str,
    pattern_id: int,
    notification_type: str,
    pattern_data: Dict,
    validation_result: Dict
) -> bool:
    """
    Create a passive notification for pattern creation.

    Returns:
        bool: Success status
    """
    try:
        logger.info(f"[NOTIFICATION] Starting creation for pattern #{pattern_id}, tenant={tenant_id}, type={notification_type}")
        # Build notification message
        if notification_type == 'pattern_created':
            title = f"New Auto-Pattern Created: {pattern_data.get('entity', 'Pattern')}"
            message = f"Based on {pattern_data.get('occurrence_count', 3)} similar transactions you classified.\n\n"
            message += f"Pattern: {pattern_data.get('description_pattern', 'N/A')}\n"
            message += f"→ Entity: {pattern_data.get('entity', 'N/A')}\n"
            message += f"→ Category: {pattern_data.get('accounting_category', 'N/A')}\n"

            if pattern_data.get('accounting_subcategory'):
                message += f"→ Subcategory: {pattern_data['accounting_subcategory']}\n"

            message += f"\nConfidence: {(pattern_data.get('confidence_score', 0) * 100):.0f}%\n"
            message += f"Risk Assessment: {validation_result.get('risk_assessment', 'medium').title()}\n"
            message += f"\nReasoning: {validation_result.get('reasoning', 'N/A')}"

            priority = 'high' if validation_result.get('risk_assessment') == 'medium' else 'normal'

        else:
            title = notification_type.replace('_', ' ').title()
            message = "Pattern status changed"
            priority = 'normal'

        # Create metadata
        metadata = {
            'pattern_id': pattern_id,
            'pattern_data': {
                'description_pattern': pattern_data.get('description_pattern'),
                'entity': pattern_data.get('entity'),
                'category': pattern_data.get('accounting_category'),
                'subcategory': pattern_data.get('accounting_subcategory'),
                'confidence': pattern_data.get('confidence_score')
            },
            'validation': {
                'is_valid': validation_result.get('is_valid'),
                'risk_assessment': validation_result.get('risk_assessment'),
                'reasoning': validation_result.get('reasoning')
            }
        }

        # Insert notification
        logger.info(f"[NOTIFICATION] Inserting into pattern_notifications table...")
        logger.info(f"[NOTIFICATION] Title: {title[:80]}...")
        logger.info(f"[NOTIFICATION] Message length: {len(message)} chars")

        cursor.execute("""
            INSERT INTO pattern_notifications (
                tenant_id, pattern_id, notification_type, title, message, metadata, priority
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            tenant_id,
            pattern_id,
            notification_type,
            title,
            message,
            json.dumps(metadata),
            priority
        ))

        notification_id = cursor.fetchone()[0]
        logger.info(f"[NOTIFICATION] INSERT successful, notification_id={notification_id}")

        conn.commit()
        logger.info(f"[NOTIFICATION] COMMIT successful")

        logger.info(f"✅ Created {notification_type} notification #{notification_id} for pattern #{pattern_id}")

        return True

    except Exception as e:
        logger.error(f"❌ [NOTIFICATION] Error creating pattern notification: {e}", exc_info=True)
        try:
            conn.rollback()
            logger.info(f"[NOTIFICATION] Rolled back transaction")
        except:
            pass
        return False


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def run_async(coro):
    """Helper to run async functions in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
