#!/usr/bin/env python3
"""
Manually trigger LLM validation for pending pattern suggestions
"""
import sys
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_ui'))

from pattern_learning import process_pending_pattern_suggestions
from anthropic import Anthropic

# Initialize Claude client with API key from environment
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    print("ERROR: ANTHROPIC_API_KEY not found in environment")
    print("Please set it in your .env file or environment variables")
    sys.exit(1)

claude_client = Anthropic(api_key=api_key)

async def main():
    tenant_id = 'delta'

    print("=" * 70)
    print("LLM PATTERN VALIDATION")
    print("=" * 70)
    print(f"\nProcessing pending pattern suggestions for tenant: {tenant_id}\n")

    # Process pending suggestions
    processed_count = await process_pending_pattern_suggestions(tenant_id, claude_client)

    print("\n" + "=" * 70)
    print(f"COMPLETED: Processed {processed_count} pattern suggestion(s)")
    print("=" * 70)
    print("\nCheck the Notifications tab to see the results!")
    print("\n")

if __name__ == "__main__":
    asyncio.run(main())
