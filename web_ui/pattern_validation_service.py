"""
Pattern Validation Background Service

This service listens for PostgreSQL NOTIFY events when new pattern suggestions
are created and automatically validates them with Claude LLM in the background.

Usage:
    Run as a background process: python pattern_validation_service.py
    Or integrate into Flask app startup

Performance optimizations:
    - Singleton pattern prevents duplicate service instances
    - Deduplication prevents processing same suggestion multiple times
    - Lock file prevents race conditions in multi-process environments
"""

import os
import sys
import asyncio
import logging
import select
import json
import threading
import time
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

# Singleton and deduplication state
_listener_started = False
_listener_lock = threading.Lock()
_recently_processed = set()  # Track recently processed suggestion IDs
_recently_processed_lock = threading.Lock()
_DEDUP_WINDOW_SECONDS = 60  # Ignore duplicate notifications within 60 seconds

# Request coalescing state
_COALESCE_WINDOW_SECONDS = 5  # Wait 5 seconds to collect notifications
_pending_notifications = []  # Queue of notifications waiting to be processed
_pending_notifications_lock = threading.Lock()
_coalesce_timer = None  # Timer for coalescing window


def initialize_claude_client():
    """Initialize Claude API client"""
    global claude_client

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment")
        raise ValueError("ANTHROPIC_API_KEY must be set")

    claude_client = Anthropic(api_key=api_key)
    logger.info("Claude API client initialized")


def _is_recently_processed(suggestion_id: int) -> bool:
    """Check if suggestion was recently processed (deduplication)"""
    with _recently_processed_lock:
        return suggestion_id in _recently_processed


def _mark_as_processed(suggestion_id: int):
    """Mark suggestion as processed and schedule cleanup"""
    with _recently_processed_lock:
        _recently_processed.add(suggestion_id)

    # Schedule cleanup after dedup window
    def cleanup():
        time.sleep(_DEDUP_WINDOW_SECONDS)
        with _recently_processed_lock:
            _recently_processed.discard(suggestion_id)

    threading.Thread(target=cleanup, daemon=True).start()


def _process_coalesced_notifications():
    """
    Process all queued notifications as a single batch.
    Called after the coalesce window expires.
    """
    global _coalesce_timer

    with _pending_notifications_lock:
        if not _pending_notifications:
            return

        # Get unique tenant_ids from queued notifications
        tenant_ids = set()
        for payload in _pending_notifications:
            try:
                data = json.loads(payload)
                tenant_id = data.get('tenant_id')
                if tenant_id:
                    tenant_ids.add(tenant_id)
            except:
                pass

        notification_count = len(_pending_notifications)
        _pending_notifications.clear()
        _coalesce_timer = None

    logger.info(f"[COALESCE] Processing {notification_count} coalesced notifications for {len(tenant_ids)} tenant(s)")

    # Process each tenant's pending suggestions ONCE
    for tenant_id in tenant_ids:
        try:
            processed = asyncio.run(process_pending_pattern_suggestions(tenant_id, claude_client))
            if processed > 0:
                logger.info(f"[COALESCE] Processed {processed} pattern(s) for tenant {tenant_id}")
        except Exception as e:
            logger.error(f"[COALESCE] Error processing patterns for tenant {tenant_id}: {e}")


def _queue_notification(payload: str):
    """
    Queue a notification for coalesced processing.
    Resets the coalesce timer each time a new notification arrives.
    """
    global _coalesce_timer

    with _pending_notifications_lock:
        _pending_notifications.append(payload)

        # Cancel existing timer if any
        if _coalesce_timer:
            _coalesce_timer.cancel()

        # Start new timer - will fire after COALESCE_WINDOW_SECONDS of inactivity
        _coalesce_timer = threading.Timer(_COALESCE_WINDOW_SECONDS, _process_coalesced_notifications)
        _coalesce_timer.daemon = True
        _coalesce_timer.start()

        logger.info(f"[COALESCE] Queued notification ({len(_pending_notifications)} pending), timer reset to {_COALESCE_WINDOW_SECONDS}s")


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

        # Deduplication check - skip if recently processed
        if _is_recently_processed(suggestion_id):
            logger.info(f"[DEDUP] Skipping duplicate notification for suggestion #{suggestion_id}")
            return

        # Mark as being processed
        _mark_as_processed(suggestion_id)

        logger.info(f"New pattern suggestion #{suggestion_id} for tenant {tenant_id} ({occurrence_count} occurrences)")

        # Process this specific pattern suggestion
        processed = await process_pending_pattern_suggestions(tenant_id, claude_client)

        if processed > 0:
            logger.info(f"Successfully processed {processed} pattern(s)")
        else:
            logger.info(f"No patterns processed (may have been rejected or already validated)")

    except Exception as e:
        logger.error(f"Error handling pattern notification: {e}", exc_info=True)


def start_listener():
    """
    Start listening for PostgreSQL NOTIFY events on 'new_pattern_suggestion' channel.
    Includes automatic reconnection logic for resilience.

    Uses singleton pattern to prevent duplicate instances in Flask debug mode.
    """
    global _listener_started

    # Singleton check - prevent duplicate listeners
    with _listener_lock:
        if _listener_started:
            logger.warning("[SINGLETON] Pattern validation service already running, skipping duplicate start")
            return
        _listener_started = True

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

                # Process notifications - use coalescing for performance
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    logger.info(f"Received notification: {notify.payload}")

                    # Queue notification for coalesced processing
                    # Instead of processing immediately, wait for more notifications
                    _queue_notification(notify.payload)

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
