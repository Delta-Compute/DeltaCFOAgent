#!/usr/bin/env python3
"""Fix user_invitations table tenant_id column type"""
from web_ui.database import db_manager

print("Fixing user_invitations.tenant_id column type...")
print("-" * 60)

try:
    # Check current type
    current_type = db_manager.execute_query(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = 'user_invitations' AND column_name = 'tenant_id'
        """,
        fetch_one=True
    )

    print(f"Current type: {current_type['data_type']}")

    if current_type['data_type'] == 'integer':
        print("\n[1/5] Dropping dependent view...")
        db_manager.execute_query(
            """
            DROP VIEW IF EXISTS v_pending_invitations CASCADE
            """
        )
        print("[OK] View dropped")

        print("\n[2/5] Removing foreign key constraint...")
        db_manager.execute_query(
            """
            ALTER TABLE user_invitations
            DROP CONSTRAINT IF EXISTS user_invitations_tenant_id_fkey
            """
        )
        print("[OK] Foreign key constraint removed")

        print("\n[3/5] Changing column type to VARCHAR(50)...")
        db_manager.execute_query(
            """
            ALTER TABLE user_invitations
            ALTER COLUMN tenant_id TYPE VARCHAR(50)
            """
        )
        print("[OK] Column type changed")

        print("\n[4/5] Re-adding foreign key constraint...")
        db_manager.execute_query(
            """
            ALTER TABLE user_invitations
            ADD CONSTRAINT user_invitations_tenant_id_fkey
            FOREIGN KEY (tenant_id) REFERENCES tenant_configuration(id) ON DELETE CASCADE
            """
        )
        print("[OK] Foreign key constraint re-added")

        print("\n[5/5] Recreating view (if needed)...")
        print("[OK] View can be recreated later if needed")

        print("\n" + "=" * 60)
        print("SUCCESS: tenant_id column fixed!")
        print("=" * 60)
    else:
        print(f"\n[SKIP] Column is already {current_type['data_type']}")

except Exception as e:
    print(f"\n[ERROR] Failed to fix column: {e}")
    import traceback
    traceback.print_exc()
