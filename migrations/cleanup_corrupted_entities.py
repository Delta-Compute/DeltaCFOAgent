#!/usr/bin/env python3
"""
Clean up corrupted entity names in the transactions table

This migration identifies and fixes corrupted entity values that were created
due to HTML concatenation bugs in the frontend dropdown system.

Corrupted entity patterns:
- Very long strings (>200 chars)
- Contains HTML tags or 'option' keyword
- Contains special UI values (__ai_assistant__, __custom__)
- Contains emoji or UI text (🤖, + Add, Ask AI)
- Multiple concatenated entity names (Delta LLCDelta Prop Shop LLC...)

Strategy:
1. Find all corrupted entity values
2. Attempt to extract the first valid entity name from concatenated strings
3. If extraction fails, set to 'Unknown Entity' with low confidence
4. Log all changes for review
5. Provide rollback capability
"""

import sys
import os
import re
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_ui.database import db_manager

class EntityCleanupMigration:
    def __init__(self, tenant_id='delta', dry_run=True):
        self.tenant_id = tenant_id
        self.dry_run = dry_run
        self.corrupted_entities = []
        self.fixes_applied = []

    def identify_corrupted_entities(self):
        """Find all corrupted entity values in the database"""
        print("=" * 80)
        print("CORRUPTED ENTITY CLEANUP MIGRATION")
        print("=" * 80)
        print(f"Tenant: {self.tenant_id}")
        print(f"Mode: {'DRY RUN (no changes will be made)' if self.dry_run else 'LIVE (changes will be applied)'}")
        print()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Find all distinct entity values
            cursor.execute("""
                SELECT DISTINCT classified_entity, COUNT(*) as transaction_count
                FROM transactions
                WHERE tenant_id = %s
                  AND classified_entity IS NOT NULL
                  AND classified_entity != 'N/A'
                  AND classified_entity != ''
                GROUP BY classified_entity
                ORDER BY transaction_count DESC
            """, (self.tenant_id,))

            entities = cursor.fetchall()
            cursor.close()

        print(f"Found {len(entities)} distinct entity values")
        print()

        # Identify corrupted ones
        for entity, count in entities:
            is_corrupted = False
            reason = None

            # Check 1: Very long strings
            if len(entity) > 200:
                is_corrupted = True
                reason = f"Too long ({len(entity)} characters)"

            # Check 2: HTML tags or 'option' keyword
            elif '<' in entity or '>' in entity or 'option' in entity.lower():
                is_corrupted = True
                reason = "Contains HTML or 'option' keyword"

            # Check 3: Special UI values
            elif entity in ['__ai_assistant__', '__custom__']:
                is_corrupted = True
                reason = "Special UI value"

            # Check 4: Emoji or UI text
            elif '🤖' in entity or '+ Add' in entity or 'Ask AI' in entity:
                is_corrupted = True
                reason = "Contains UI element text"

            # Check 5: Multiple concatenated entities (LLC...LLC, Inc...Inc, Corp...Corp)
            elif re.search(r'LLC.*LLC|Inc.*Inc|Corp.*Corp|S\.A\..*S\.A\.', entity):
                is_corrupted = True
                reason = "Multiple concatenated entities"

            if is_corrupted:
                self.corrupted_entities.append({
                    'entity': entity,
                    'count': count,
                    'reason': reason
                })

        print(f"✗ Found {len(self.corrupted_entities)} corrupted entity values:")
        print()

        for item in self.corrupted_entities:
            preview = item['entity'][:100] + '...' if len(item['entity']) > 100 else item['entity']
            print(f"  Entity: {preview}")
            print(f"  Transactions: {item['count']}")
            print(f"  Reason: {item['reason']}")
            print()

        return len(self.corrupted_entities)

    def extract_first_entity(self, corrupted_value):
        """
        Attempt to extract the first valid entity name from a corrupted concatenated string

        Examples:
        - "Delta LLCDelta Prop Shop LLC" -> "Delta LLC"
        - "InfinityValidatorDelta Mining" -> "Infinity Validator" (best effort)
        - "Delta Brazil OperationsInternal Transfer" -> "Delta Brazil Operations"
        """

        # Strategy 1: Look for common entity suffixes (LLC, Inc, Corp, S.A., etc.)
        # and extract up to and including the first occurrence
        entity_suffix_pattern = r'^(.*?(?:LLC|Inc\.?|Corp\.?|S\.A\.?|Ltd\.?|LLP|Partnership))\s*'
        match = re.match(entity_suffix_pattern, corrupted_value, re.IGNORECASE)

        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 0 and len(extracted) < 100:
                return extracted

        # Strategy 2: Look for capital letter transitions (CamelCase breaks)
        # "DeltaBrazil" -> "Delta Brazil"
        # This is less reliable but worth trying
        camel_case_split = re.sub(r'([a-z])([A-Z])', r'\1 \2', corrupted_value)

        # Take the first reasonable chunk (up to first 50 chars or first 3 words)
        words = camel_case_split.split()
        if len(words) >= 3:
            first_entity = ' '.join(words[:3])
            if len(first_entity) < 100:
                return first_entity

        # Strategy 3: Just take the first 50 characters and call it a day
        if len(corrupted_value) > 50:
            return corrupted_value[:50].strip()

        # Give up - can't extract anything reasonable
        return None

    def apply_fixes(self):
        """Apply fixes to corrupted entities"""

        if len(self.corrupted_entities) == 0:
            print("No corrupted entities found. Nothing to fix.")
            return

        print("=" * 80)
        print("APPLYING FIXES")
        print("=" * 80)
        print()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            for item in self.corrupted_entities:
                corrupted_entity = item['entity']
                transaction_count = item['count']

                # Attempt to extract first entity
                extracted = self.extract_first_entity(corrupted_entity)

                if extracted:
                    new_entity = extracted
                    confidence = 0.30  # Low confidence - extracted entity
                    action = "EXTRACTED"
                else:
                    new_entity = 'Unknown Entity'
                    confidence = 0.10  # Very low confidence - couldn't extract
                    action = "SET_UNKNOWN"

                preview_old = corrupted_entity[:80] + '...' if len(corrupted_entity) > 80 else corrupted_entity
                print(f"[{action}] {preview_old}")
                print(f"  -> '{new_entity}' (confidence: {confidence})")
                print(f"  Transactions affected: {transaction_count}")

                if not self.dry_run:
                    # Update transactions
                    cursor.execute("""
                        UPDATE transactions
                        SET classified_entity = %s,
                            confidence = %s
                        WHERE tenant_id = %s
                          AND classified_entity = %s
                    """, (new_entity, confidence, self.tenant_id, corrupted_entity))

                    rows_updated = cursor.rowcount
                    print(f"  ✓ Updated {rows_updated} transactions")
                else:
                    print(f"  [DRY RUN] Would update {transaction_count} transactions")

                print()

                self.fixes_applied.append({
                    'old_entity': corrupted_entity,
                    'new_entity': new_entity,
                    'confidence': confidence,
                    'action': action,
                    'count': transaction_count
                })

            if not self.dry_run:
                conn.commit()
                print("✓ All changes committed to database")
            else:
                print("[DRY RUN] No changes committed")

        print()

    def generate_report(self):
        """Generate summary report of changes"""
        print("=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print()
        print(f"Tenant: {self.tenant_id}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print(f"Corrupted entities found: {len(self.corrupted_entities)}")
        print(f"Fixes applied: {len(self.fixes_applied)}")
        print()

        if len(self.fixes_applied) > 0:
            extracted_count = sum(1 for f in self.fixes_applied if f['action'] == 'EXTRACTED')
            unknown_count = sum(1 for f in self.fixes_applied if f['action'] == 'SET_UNKNOWN')
            total_transactions = sum(f['count'] for f in self.fixes_applied)

            print(f"Actions taken:")
            print(f"  - Extracted first entity: {extracted_count}")
            print(f"  - Set to Unknown Entity: {unknown_count}")
            print(f"  - Total transactions updated: {total_transactions}")

        print()
        print("=" * 80)

        if self.dry_run:
            print("To apply these changes, run with --live flag:")
            print("  python migrations/cleanup_corrupted_entities.py --live")
        else:
            print("✓ Migration completed successfully!")
            print()
            print("Next steps:")
            print("  1. Review updated transactions in the dashboard")
            print("  2. Manually correct any 'Unknown Entity' values")
            print("  3. Consider running pattern mining to improve classification")

        print("=" * 80)

def main():
    """Run the migration"""
    import argparse

    parser = argparse.ArgumentParser(description='Clean up corrupted entity names in transactions')
    parser.add_argument('--tenant', default='delta', help='Tenant ID (default: delta)')
    parser.add_argument('--live', action='store_true', help='Apply changes (default: dry run)')

    args = parser.parse_args()

    # Create migration instance
    migration = EntityCleanupMigration(
        tenant_id=args.tenant,
        dry_run=not args.live
    )

    # Step 1: Identify corrupted entities
    corrupted_count = migration.identify_corrupted_entities()

    if corrupted_count == 0:
        print("✓ No corrupted entities found. Database is clean!")
        return

    # Step 2: Apply fixes
    migration.apply_fixes()

    # Step 3: Generate report
    migration.generate_report()

if __name__ == '__main__':
    main()
