#!/usr/bin/env python3
"""
Analyze existing classified transactions and auto-generate classification patterns

This script mines the Delta tenant's existing transaction data to discover
patterns based on ACTUAL user classifications, not hardcoded assumptions.

Strategy:
1. Find high-frequency description → entity/category mappings
2. Extract common keywords and phrases
3. Calculate confidence scores based on consistency
4. Generate patterns that would correctly classify existing transactions
5. Test patterns against existing data for accuracy
"""

import sys
import os
import re
from collections import defaultdict, Counter
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_ui.database import db_manager

class PatternMiner:
    def __init__(self, tenant_id='delta'):
        self.tenant_id = tenant_id
        self.transactions = []
        self.generated_patterns = []

    def load_transactions(self):
        """Load all classified transactions for analysis"""
        print("=" * 80)
        print("PATTERN MINING: Analyzing Existing Transactions")
        print("=" * 80)
        print(f"Tenant: {self.tenant_id}")
        print()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Load transactions with classifications
            # Note: Using actual column names from production schema
            cursor.execute("""
                SELECT
                    description, amount, accounting_category, subcategory,
                    classified_entity, origin, destination, confidence,
                    date, tenant_id
                FROM transactions
                WHERE classified_entity IS NOT NULL
                  AND classified_entity NOT IN ('Unknown Entity', 'Unknown', '', 'nan', 'NaN')
                  AND (tenant_id = %s OR tenant_id IS NULL)
                ORDER BY date DESC
                LIMIT 5000
            """, (self.tenant_id,))

            rows = cursor.fetchall()

            for row in rows:
                self.transactions.append({
                    'description': row[0],
                    'amount': float(row[1]) if row[1] else 0.0,
                    'category': row[2],
                    'subcategory': row[3],
                    'entity': row[4],
                    'origin': row[5],
                    'destination': row[6],
                    'confidence': float(row[7]) if row[7] else 0.0,
                    'date': row[8]
                })

            cursor.close()

        print(f"✓ Loaded {len(self.transactions)} classified transactions")
        print()

    def extract_keywords(self, description):
        """Extract meaningful keywords from description"""
        # Remove common noise words
        noise_words = {
            'THE', 'A', 'AN', 'AND', 'OR', 'BUT', 'IN', 'ON', 'AT', 'TO', 'FOR',
            'OF', 'WITH', 'BY', 'FROM', 'AS', 'IS', 'WAS', 'ARE', 'WERE', 'BEEN',
            'BE', 'HAVE', 'HAS', 'HAD', 'DO', 'DOES', 'DID', 'WILL', 'WOULD',
            'COULD', 'SHOULD', 'MAY', 'MIGHT', 'MUST', 'CAN'
        }

        # Clean and tokenize
        desc_upper = description.upper()
        # Remove special characters but keep spaces and alphanumeric
        cleaned = re.sub(r'[^A-Z0-9\s\-]', ' ', desc_upper)
        tokens = cleaned.split()

        # Filter noise words and short tokens
        keywords = [t for t in tokens if t not in noise_words and len(t) >= 3]

        return keywords

    def find_common_phrases(self, descriptions):
        """Find common multi-word phrases in descriptions"""
        phrases = Counter()

        for desc in descriptions:
            desc_upper = desc.upper()
            words = desc_upper.split()

            # 2-word phrases
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                if len(phrase) >= 6:  # Meaningful length
                    phrases[phrase] += 1

            # 3-word phrases
            for i in range(len(words) - 2):
                phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                if len(phrase) >= 10:
                    phrases[phrase] += 1

        return phrases

    def mine_patterns(self):
        """Mine patterns from transaction data"""
        print("[1/4] Mining patterns from transaction descriptions...")
        print()

        # Group transactions by entity
        entity_groups = defaultdict(list)
        for txn in self.transactions:
            entity_groups[txn['entity']].append(txn)

        print(f"Found {len(entity_groups)} unique entities:")
        for entity, txns in sorted(entity_groups.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  - {entity}: {len(txns)} transactions")
        print()

        # For each entity, find common patterns
        print("[2/4] Analyzing description patterns per entity...")
        print()

        for entity, txns in entity_groups.items():
            if len(txns) < 3:  # Need at least 3 transactions to establish pattern
                continue

            # Analyze keywords
            keyword_freq = Counter()
            for txn in txns:
                keywords = self.extract_keywords(txn['description'])
                keyword_freq.update(keywords)

            # Find phrases
            descriptions = [txn['description'] for txn in txns]
            phrase_freq = self.find_common_phrases(descriptions)

            # Get category consistency
            category_dist = Counter([txn['category'] for txn in txns if txn['category']])
            subcategory_dist = Counter([txn['subcategory'] for txn in txns if txn['subcategory']])

            most_common_category = category_dist.most_common(1)[0] if category_dist else ('Unknown', 0)
            most_common_subcategory = subcategory_dist.most_common(1)[0] if subcategory_dist else (None, 0)

            # Generate patterns for high-frequency keywords/phrases
            # Keyword patterns (appear in >30% of transactions for this entity)
            threshold = max(3, len(txns) * 0.3)

            for keyword, count in keyword_freq.most_common(10):
                if count >= threshold:
                    confidence = count / len(txns)

                    # Calculate priority based on specificity
                    priority = 400  # Base priority for mined patterns

                    # Higher priority for very specific keywords
                    if count / len(txns) > 0.8:
                        priority = 350

                    # Check if this keyword is unique to this entity
                    other_entity_count = 0
                    for other_entity, other_txns in entity_groups.items():
                        if other_entity != entity:
                            for other_txn in other_txns:
                                if keyword in other_txn['description'].upper():
                                    other_entity_count += 1

                    # If keyword is highly specific to this entity, boost priority
                    if other_entity_count < count * 0.2:  # <20% false positives
                        priority -= 50

                    pattern = {
                        'pattern_type': 'mined_keyword',
                        'description_pattern': f'%{keyword}%',
                        'entity': entity,
                        'accounting_category': most_common_category[0],
                        'subcategory': most_common_subcategory[0] if most_common_subcategory else None,
                        'confidence_score': round(confidence, 2),
                        'priority': priority,
                        'support_count': count,
                        'total_transactions': len(txns),
                        'support_percentage': round(confidence * 100, 1),
                        'notes': f'Auto-generated: "{keyword}" appears in {count}/{len(txns)} ({round(confidence*100,1)}%) transactions for {entity}'
                    }

                    self.generated_patterns.append(pattern)

            # Phrase patterns (appear in >20% of transactions)
            phrase_threshold = max(2, len(txns) * 0.2)

            for phrase, count in phrase_freq.most_common(5):
                if count >= phrase_threshold:
                    confidence = count / len(txns)

                    # Phrases are more specific, so higher base priority
                    priority = 350

                    if confidence > 0.5:
                        priority = 320

                    pattern = {
                        'pattern_type': 'mined_phrase',
                        'description_pattern': f'%{phrase}%',
                        'entity': entity,
                        'accounting_category': most_common_category[0],
                        'subcategory': most_common_subcategory[0] if most_common_subcategory else None,
                        'confidence_score': round(confidence, 2),
                        'priority': priority,
                        'support_count': count,
                        'total_transactions': len(txns),
                        'support_percentage': round(confidence * 100, 1),
                        'notes': f'Auto-generated: "{phrase}" appears in {count}/{len(txns)} ({round(confidence*100,1)}%) transactions for {entity}'
                    }

                    self.generated_patterns.append(pattern)

        print(f"✓ Generated {len(self.generated_patterns)} candidate patterns")
        print()

    def test_patterns(self):
        """Test generated patterns against existing transactions"""
        print("[3/4] Testing patterns against existing transactions...")
        print()

        # Sort patterns by priority (lower = higher priority)
        sorted_patterns = sorted(self.generated_patterns, key=lambda p: p['priority'])

        correct_matches = 0
        incorrect_matches = 0
        no_match = 0

        match_details = []

        for txn in self.transactions:
            matched_pattern = None

            # Try to match with generated patterns
            for pattern in sorted_patterns:
                pattern_keyword = pattern['description_pattern'].strip('%')
                if pattern_keyword in txn['description'].upper():
                    matched_pattern = pattern
                    break

            if matched_pattern:
                if matched_pattern['entity'] == txn['entity']:
                    correct_matches += 1
                else:
                    incorrect_matches += 1
                    match_details.append({
                        'description': txn['description'],
                        'actual_entity': txn['entity'],
                        'predicted_entity': matched_pattern['entity'],
                        'pattern': matched_pattern['description_pattern']
                    })
            else:
                no_match += 1

        total = len(self.transactions)
        accuracy = (correct_matches / total * 100) if total > 0 else 0
        coverage = ((correct_matches + incorrect_matches) / total * 100) if total > 0 else 0

        print(f"Test Results:")
        print(f"  ✓ Correct matches: {correct_matches} ({correct_matches/total*100:.1f}%)")
        print(f"  ✗ Incorrect matches: {incorrect_matches} ({incorrect_matches/total*100:.1f}%)")
        print(f"  ○ No match: {no_match} ({no_match/total*100:.1f}%)")
        print(f"  Accuracy: {accuracy:.1f}%")
        print(f"  Coverage: {coverage:.1f}%")
        print()

        # Show sample mismatches
        if match_details:
            print("Sample mismatches (first 10):")
            for detail in match_details[:10]:
                print(f"  Description: {detail['description'][:60]}")
                print(f"    Actual: {detail['actual_entity']}")
                print(f"    Predicted: {detail['predicted_entity']} (pattern: {detail['pattern']})")
                print()

        return {
            'correct': correct_matches,
            'incorrect': incorrect_matches,
            'no_match': no_match,
            'accuracy': accuracy,
            'coverage': coverage
        }

    def generate_report(self):
        """Generate detailed report of mined patterns"""
        print("[4/4] Generating pattern report...")
        print()

        # Group by entity
        entity_patterns = defaultdict(list)
        for pattern in self.generated_patterns:
            entity_patterns[pattern['entity']].append(pattern)

        print("=" * 80)
        print("MINED CLASSIFICATION PATTERNS REPORT")
        print("=" * 80)
        print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Tenant: {self.tenant_id}")
        print(f"Transactions analyzed: {len(self.transactions)}")
        print(f"Patterns generated: {len(self.generated_patterns)}")
        print()

        for entity in sorted(entity_patterns.keys()):
            patterns = entity_patterns[entity]
            print(f"\n{'='*80}")
            print(f"ENTITY: {entity}")
            print(f"{'='*80}")
            print(f"Patterns: {len(patterns)}\n")

            # Sort by confidence
            for pattern in sorted(patterns, key=lambda p: p['confidence_score'], reverse=True):
                print(f"Pattern: {pattern['description_pattern']}")
                print(f"  Type: {pattern['pattern_type']}")
                print(f"  Category: {pattern['accounting_category']}")
                if pattern['subcategory']:
                    print(f"  Subcategory: {pattern['subcategory']}")
                print(f"  Confidence: {pattern['confidence_score']} ({pattern['support_percentage']}%)")
                print(f"  Priority: {pattern['priority']}")
                print(f"  Support: {pattern['support_count']}/{pattern['total_transactions']} transactions")
                print(f"  Notes: {pattern['notes']}")
                print()

        # Summary by confidence tier
        print("\n" + "="*80)
        print("CONFIDENCE DISTRIBUTION")
        print("="*80)

        high_conf = [p for p in self.generated_patterns if p['confidence_score'] >= 0.8]
        med_conf = [p for p in self.generated_patterns if 0.5 <= p['confidence_score'] < 0.8]
        low_conf = [p for p in self.generated_patterns if p['confidence_score'] < 0.5]

        print(f"High confidence (≥80%): {len(high_conf)} patterns")
        print(f"Medium confidence (50-79%): {len(med_conf)} patterns")
        print(f"Low confidence (<50%): {len(low_conf)} patterns")
        print()

        return entity_patterns

def main():
    """Run pattern mining analysis"""
    miner = PatternMiner(tenant_id='delta')

    # Step 1: Load data
    miner.load_transactions()

    if len(miner.transactions) == 0:
        print("❌ No classified transactions found for analysis")
        return

    # Step 2: Mine patterns
    miner.mine_patterns()

    # Step 3: Test patterns
    test_results = miner.test_patterns()

    # Step 4: Generate report
    entity_patterns = miner.generate_report()

    # Final summary
    print("=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print()

    if test_results['accuracy'] >= 80:
        print("✅ EXCELLENT: Patterns achieve >80% accuracy")
        print("   Recommendation: Safe to use these patterns for classification")
    elif test_results['accuracy'] >= 60:
        print("⚠️  GOOD: Patterns achieve 60-80% accuracy")
        print("   Recommendation: Use with human review for edge cases")
    else:
        print("❌ NEEDS IMPROVEMENT: Patterns achieve <60% accuracy")
        print("   Recommendation: Need more training data or refinement")

    print()
    print(f"Coverage: {test_results['coverage']:.1f}% of transactions matched")
    print(f"No match: {test_results['no_match']} transactions need additional patterns")
    print()
    print("=" * 80)

if __name__ == '__main__':
    main()
