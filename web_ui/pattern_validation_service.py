"""
Pattern Validation Background Service

This service listens for PostgreSQL NOTIFY events when new pattern suggestions
are created and automatically validates them with Claude LLM in the background.

Usage:
    Run as a background process: python pattern_validation_service.py
    Or integrate into Flask app startup
"""

import os
import sys
import asyncio
import logging
import select
import json
from anthropic import Anthropic

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from database import db_manager
from pattern_learning import process_pending_pattern_suggestions

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Claude client
claude_client = None


def initialize_claude_client():
    """Initialize Claude API client"""
    global claude_client

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment")
        raise ValueError("ANTHROPIC_API_KEY must be set")

    claude_client = Anthropic(api_key=api_key)
    logger.info("Claude API client initialized")


async def handle_new_pattern_notification(payload):
    """
    Handle notification about new pattern suggestion

    Args:
        payload: JSON payload from PostgreSQL NOTIFY
    """
    try:
        data = json.loads(payload)
        suggestion_id = data.get('suggestion_id')
        tenant_id = data.get('tenant_id')
        occurrence_count = data.get('occurrence_count')

        logger.info(f"🔔 New pattern suggestion #{suggestion_id} for tenant {tenant_id} ({occurrence_count} occurrences)")

        # Process this specific pattern suggestion
        processed = await process_pending_pattern_suggestions(tenant_id, claude_client)

        if processed > 0:
            logger.info(f"✅ Successfully processed {processed} pattern(s)")
        else:
            logger.warning(f"⚠️ No patterns were processed (may have been rejected)")

    except Exception as e:
        logger.error(f"❌ Error handling pattern notification: {e}", exc_info=True)


def start_listener():
    """
    Start listening for PostgreSQL NOTIFY events on 'new_pattern_suggestion' channel.
    Includes automatic reconnection logic for resilience.
    """
    logger.info("Starting Pattern Validation Service...")

    # Initialize Claude client
    initialize_claude_client()

    reconnect_delay = 5  # Start with 5 seconds
    max_reconnect_delay = 300  # Max 5 minutes between retries

    while True:
        conn = None
        cursor = None
        try:
            # Get a dedicated connection for LISTEN
            conn = db_manager._get_postgresql_connection()
            conn.set_isolation_level(0)  # Set to autocommit mode
            cursor = conn.cursor()

            # Start listening
            cursor.execute("LISTEN new_pattern_suggestion;")
            logger.info("Listening for new pattern suggestions...")

            # Reset reconnect delay on successful connection
            reconnect_delay = 5

            while True:
                # Wait for notifications (with 30 second timeout)
                if select.select([conn], [], [], 30) == ([], [], []):
                    # Timeout - check connection is still alive
                    try:
                        cursor.execute("SELECT 1")
                    except Exception:
                        logger.warning("Connection check failed, reconnecting...")
                        break
                    continue

                # Process notifications
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    logger.info(f"Received notification: {notify.payload}")

                    # Handle notification asynchronously
                    try:
                        asyncio.run(handle_new_pattern_notification(notify.payload))
                    except Exception as e:
                        logger.error(f"Error processing notification: {e}")

        except KeyboardInterrupt:
            logger.info("Stopping Pattern Validation Service...")
            break

        except Exception as e:
            logger.error(f"Listener error: {e}. Reconnecting in {reconnect_delay}s...")

        finally:
            # Clean up connection
            if cursor:
                try:
                    cursor.execute("UNLISTEN new_pattern_suggestion;")
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        # Wait before reconnecting (exponential backoff)
        import time
        time.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

    logger.info("Service stopped")


if __name__ == '__main__':
    start_listener()
