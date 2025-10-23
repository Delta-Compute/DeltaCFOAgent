"""
Pytest Configuration and Shared Fixtures
Phase 0: Basic fixtures for database and API testing
"""

import pytest
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope='session')
def test_env():
    """
    Set up test environment variables
    Ensures tests use test database and configurations
    """
    original_env = dict(os.environ)

    # Set test environment variables
    os.environ['DB_TYPE'] = 'postgresql'
    os.environ['DB_NAME'] = os.getenv('TEST_DB_NAME', os.getenv('DB_NAME', 'delta_cfo'))
    os.environ['DB_HOST'] = os.getenv('TEST_DB_HOST', os.getenv('DB_HOST', '34.39.143.82'))
    os.environ['DB_PORT'] = os.getenv('TEST_DB_PORT', os.getenv('DB_PORT', '5432'))
    os.environ['DB_USER'] = os.getenv('TEST_DB_USER', os.getenv('DB_USER', 'delta_user'))
    os.environ['DB_PASSWORD'] = os.getenv('TEST_DB_PASSWORD', os.getenv('DB_PASSWORD', ''))

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def db_manager(test_env):
    """
    Provide DatabaseManager instance for tests
    Uses test environment configuration
    """
    from web_ui.database import DatabaseManager

    manager = DatabaseManager()
    yield manager

    # Cleanup: Close any open connections
    if hasattr(manager, 'connection_pool') and manager.connection_pool:
        manager.connection_pool.closeall()


@pytest.fixture
def flask_app(test_env):
    """
    Provide Flask app instance for API testing
    Configured for testing mode
    """
    from web_ui.app_db import app

    app.config['TESTING'] = True
    app.config['DEBUG'] = False

    yield app


@pytest.fixture
def api_client(flask_app):
    """
    Provide Flask test client for API endpoint testing
    """
    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def sample_transaction():
    """
    Provide sample transaction data for testing
    """
    return {
        'date': '2025-01-15',
        'description': 'TEST_TRANSACTION_SAMPLE',
        'amount': 100.00,
        'category': 'Test',
        'entity': 'Test Entity'
    }


@pytest.fixture
def cleanup_test_data(db_manager):
    """
    Cleanup test data after tests
    Removes any records with TEST_ prefix
    """
    yield

    # Cleanup after test
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            # Clean up test transactions
            cursor.execute("""
                DELETE FROM transactions
                WHERE description LIKE 'TEST_%'
                OR description LIKE '%_TEST_%'
            """)
            conn.commit()
    except Exception as e:
        # Don't fail tests if cleanup fails
        print(f"Warning: Cleanup failed: {e}")
