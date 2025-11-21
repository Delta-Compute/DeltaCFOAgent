#!/usr/bin/env python3
"""
One-time script to process existing pending pattern suggestions

This processes the 3 pending patterns that were created before the
pattern validation service was fixed.
"""

import os
import sys
import asyncio
from anthropic import Anthropic

# Add web_ui to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_ui'))

from pattern_learning import process_pending_pattern_suggestions


async def main():
    """Process all pending patterns for delta tenant"""

    print("=" * 80)
    print("Processing Pending Pattern Suggestions")
    print("=" * 80)

    # Initialize Claude API client
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment")
        sys.exit(1)

    claude_client = Anthropic(api_key=api_key)
    print(f"Claude API client initialized (key: {api_key[:12]}...)")

    # Process patterns for delta tenant
    tenant_id = 'delta'

    print(f"\nProcessing pending patterns for tenant: {tenant_id}")
    print("-" * 80)

    processed_count = await process_pending_pattern_suggestions(tenant_id, claude_client)

    print("-" * 80)
    print(f"\nRESULTS:")
    print(f"  Processed: {processed_count} pattern(s)")

    if processed_count > 0:
        print(f"\n  ✅ Success! Check:")
        print(f"     1. pattern_suggestions table (status should be approved/rejected)")
        print(f"     2. classification_patterns table (new patterns created)")
        print(f"     3. pattern_notifications table (notifications created)")
        print(f"     4. Your browser should show toast notifications!")
    else:
        print(f"\n  ⚠️  No patterns were processed")
        print(f"     - They may have all been rejected by Claude")
        print(f"     - Or they may have already been processed")

    print("=" * 80)


if __name__ == '__main__':
    asyncio.run(main())
