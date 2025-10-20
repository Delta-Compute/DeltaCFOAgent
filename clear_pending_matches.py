#!/usr/bin/env python3
"""
Script para limpar todos os pending matches para aplicar novo algoritmo
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_ui.database import db_manager

def clear_pending_matches():
    """Clear all pending matches to apply new algorithm weights"""
    try:
        # Delete all pending matches
        result = db_manager.execute_query(
            "DELETE FROM pending_invoice_matches WHERE 1=1",
            fetch_all=False
        )

        print(f"Successfully cleared all pending matches")

        # Get count to verify
        count_result = db_manager.execute_query(
            "SELECT COUNT(*) FROM pending_invoice_matches",
            fetch_all=False
        )

        if count_result:
            # PostgreSQL returns integer directly for COUNT(*)
            remaining = count_result if isinstance(count_result, int) else count_result.get('count', 0)
            print(f"Pending matches remaining: {remaining}")

        print("Ready for fresh matching with new algorithm (70% weight for amount)")
        return True

    except Exception as e:
        print(f"Error clearing pending matches: {e}")
        return False

if __name__ == "__main__":
    print("Clearing pending matches to apply new algorithm...")
    success = clear_pending_matches()

    if success:
        print("\nDone! Now run 'Run Invoice Matching' in the web interface")
        print("The new algorithm (70% weight for exact amounts) will be applied")
    else:
        print("\nFailed to clear pending matches")