#!/usr/bin/env python3
"""
Simple database connection test
"""
import os
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

def test_connection():
    """Test database connection"""
    try:
        print("=== Testing PostgreSQL Connection ===")
        print(f"Host: {os.getenv('DB_HOST')}")
        print(f"Port: {os.getenv('DB_PORT')}")
        print(f"Database: {os.getenv('DB_NAME')}")
        print(f"User: {os.getenv('DB_USER')}")
        print()

        # Connect to database
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )

        print("Connection successful!")

        # Test query
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"\nPostgreSQL version: {version}")

            # Check tables
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)

            tables = cur.fetchall()
            print(f"\nFound {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")

        conn.close()
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    test_connection()
