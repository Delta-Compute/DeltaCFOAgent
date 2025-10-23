"""
Phase 0: Basic Database Tests
==============================

Tests: 5
Purpose: Verify PostgreSQL database connection and basic operations
Coverage: Database connection, queries, transactions

Test List:
1. test_database_connection - Can we connect to PostgreSQL?
2. test_database_query_execution - Can we execute SELECT queries?
3. test_database_insert_operation - Can we insert test records?
4. test_database_transaction_rollback - Do transactions rollback correctly?
5. test_connection_pool_exists - Is connection pooling configured?
"""

import pytest


@pytest.mark.database
@pytest.mark.smoke
class TestDatabaseBasic:
    """Basic database connectivity and operation tests"""

    def test_database_connection(self, db_manager):
        """
        Test: Database connection establishment

        Given: DatabaseManager instance
        When: Requesting a database connection
        Then: Connection is established successfully
        """
        with db_manager.get_connection() as conn:
            assert conn is not None
            assert not conn.closed

    def test_database_query_execution(self, db_manager):
        """
        Test: Basic SELECT query execution

        Given: Active database connection
        When: Executing a simple SELECT query
        Then: Query executes without errors and returns results
        """
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 as test_value")
            result = cursor.fetchone()

            assert result is not None
            assert result[0] == 1

    def test_database_insert_operation(self, db_manager, sample_transaction, cleanup_test_data):
        """
        Test: Insert operation into transactions table

        Given: Sample transaction data
        When: Inserting a test transaction
        Then: Record is inserted successfully and can be retrieved

        Note: cleanup_test_data fixture removes test data after test
        """
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Insert test transaction
            cursor.execute("""
                INSERT INTO transactions (date, description, amount, category, entity)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                sample_transaction['date'],
                sample_transaction['description'],
                sample_transaction['amount'],
                sample_transaction['category'],
                sample_transaction['entity']
            ))

            inserted_id = cursor.fetchone()[0]
            conn.commit()

            # Verify insertion
            cursor.execute("""
                SELECT description, amount FROM transactions WHERE id = %s
            """, (inserted_id,))

            result = cursor.fetchone()
            assert result is not None
            assert result[0] == sample_transaction['description']
            assert float(result[1]) == sample_transaction['amount']

    def test_database_transaction_rollback(self, db_manager):
        """
        Test: Transaction rollback functionality

        Given: Active database connection with transaction
        When: Rolling back a transaction after insert
        Then: Changes are not persisted to database
        """
        test_description = 'TEST_ROLLBACK_TRANSACTION'

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Insert and rollback
            cursor.execute("""
                INSERT INTO transactions (date, description, amount)
                VALUES (%s, %s, %s)
                RETURNING id
            """, ('2025-01-01', test_description, 999.99))

            inserted_id = cursor.fetchone()[0]
            conn.rollback()  # Rollback instead of commit

            # Verify record doesn't exist
            cursor.execute("""
                SELECT id FROM transactions WHERE id = %s
            """, (inserted_id,))

            result = cursor.fetchone()
            assert result is None  # Should not exist after rollback

    def test_connection_pool_exists(self, db_manager):
        """
        Test: Connection pool configuration

        Given: DatabaseManager instance
        When: Checking for connection pool
        Then: Connection pool is configured (or gracefully not configured)

        Note: Connection pool may be None in some environments (e.g., CI)
        """
        # Check that connection_pool attribute exists
        assert hasattr(db_manager, 'connection_pool')

        # If pool exists, verify it's properly configured
        if db_manager.connection_pool is not None:
            assert db_manager.connection_pool.minconn >= 1
            assert db_manager.connection_pool.maxconn >= 1


# Additional smoke test for critical path
@pytest.mark.smoke
def test_database_health_check(db_manager):
    """
    Quick smoke test for database health
    Tests the most critical database operation
    """
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions")
        count = cursor.fetchone()[0]
        # Just verify query executes (count can be 0 or any number)
        assert count >= 0
