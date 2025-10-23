"""
Migration script to add vendor_name column to invoices table
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_ui.database import db_manager

def add_vendor_name_column():
    """Add vendor_name column to invoices table if it doesn't exist"""
    try:
        print("Starting migration: Adding vendor_name column to invoices table...")

        # Check if column already exists
        check_query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name='invoices' AND column_name='vendor_name'
        """

        result = db_manager.execute_query(check_query)

        if result and isinstance(result, list) and len(result) > 0:
            print("[SKIP] vendor_name column already exists in invoices table")
            return True

        # Add the column
        alter_query = """
        ALTER TABLE invoices
        ADD COLUMN vendor_name TEXT
        """

        db_manager.execute_query(alter_query)
        print("[SUCCESS] Added vendor_name column to invoices table")

        # Create index for better query performance
        index_query = """
        CREATE INDEX IF NOT EXISTS idx_invoices_vendor
        ON invoices(vendor_name)
        """

        db_manager.execute_query(index_query)
        print("[SUCCESS] Created index on vendor_name column")

        # Update existing NULL values to default vendor
        update_query = """
        UPDATE invoices
        SET vendor_name = 'DELTA ENERGY'
        WHERE vendor_name IS NULL OR vendor_name = ''
        """

        result = db_manager.execute_query(update_query)
        print(f"[SUCCESS] Updated existing invoices with default vendor name")

        print("\nMigration completed successfully!")
        return True

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = add_vendor_name_column()
    sys.exit(0 if success else 1)
