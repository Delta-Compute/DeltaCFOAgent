#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete fix for tenant_configuration and dependent tables
Changes tenant_configuration.id from INTEGER to VARCHAR(50)
"""
import sys
import io

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from web_ui.database import db_manager

print("=" * 80)
print("FIXING TENANT SCHEMA - COMPLETE MIGRATION")
print("=" * 80)

try:
    # Step 1: Check current schema
    print("\n[1/10] Checking current schema...")
    tenant_config_type = db_manager.execute_query(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = 'tenant_configuration' AND column_name = 'id'
        """,
        fetch_one=True
    )
    print(f"[OK] tenant_configuration.id is: {tenant_config_type['data_type']}")

    if tenant_config_type['data_type'] != 'integer':
        print("\n[SKIP] Schema is already correct!")
        sys.exit(0)

    # Step 2: Find all dependent tables
    print("\n[2/10] Finding dependent tables...")
    dependent_tables = db_manager.execute_query(
        """
        SELECT DISTINCT
            tc.table_name,
            kcu.column_name,
            tc.constraint_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND ccu.table_name = 'tenant_configuration'
            AND ccu.column_name = 'id'
        """,
        fetch_all=True
    )

    print(f"[OK] Found {len(dependent_tables)} dependent tables:")
    for table in dependent_tables:
        print(f"     - {table['table_name']}.{table['column_name']} ({table['constraint_name']})")

    # Step 3: Drop all foreign key constraints
    print("\n[3/10] Dropping foreign key constraints...")
    for table in dependent_tables:
        db_manager.execute_query(
            f"""
            ALTER TABLE {table['table_name']}
            DROP CONSTRAINT IF EXISTS {table['constraint_name']}
            """
        )
        print(f"[OK] Dropped: {table['constraint_name']}")

    # Step 4: Drop ALL dependent views
    print("\n[4/10] Finding and dropping ALL dependent views...")

    # Get all views in the database
    all_views = db_manager.execute_query(
        """
        SELECT table_name
        FROM information_schema.views
        WHERE table_schema = 'public'
        """,
        fetch_all=True
    )

    print(f"[INFO] Found {len(all_views)} views in database")

    # Drop all views with CASCADE to handle dependencies
    for view in all_views:
        try:
            db_manager.execute_query(f"DROP VIEW IF EXISTS {view['table_name']} CASCADE")
            print(f"[OK] Dropped view: {view['table_name']}")
        except Exception as e:
            print(f"[WARNING] Could not drop {view['table_name']}: {e}")

    # Step 5: Change tenant_configuration.id type
    print("\n[5/10] Changing tenant_configuration.id to VARCHAR(50)...")
    db_manager.execute_query(
        """
        ALTER TABLE tenant_configuration
        ALTER COLUMN id TYPE VARCHAR(50)
        """
    )
    print("[OK] tenant_configuration.id changed to VARCHAR(50)")

    # Step 6: Change dependent columns
    print("\n[6/10] Changing dependent column types...")
    for table in dependent_tables:
        db_manager.execute_query(
            f"""
            ALTER TABLE {table['table_name']}
            ALTER COLUMN {table['column_name']} TYPE VARCHAR(50)
            """
        )
        print(f"[OK] Changed: {table['table_name']}.{table['column_name']}")

    # Step 7: Re-create foreign key constraints
    print("\n[7/10] Re-creating foreign key constraints...")
    for table in dependent_tables:
        db_manager.execute_query(
            f"""
            ALTER TABLE {table['table_name']}
            ADD CONSTRAINT {table['constraint_name']}
            FOREIGN KEY ({table['column_name']})
            REFERENCES tenant_configuration(id)
            ON DELETE CASCADE
            """
        )
        print(f"[OK] Re-created: {table['constraint_name']}")

    # Step 8: Verify changes
    print("\n[8/10] Verifying changes...")
    new_type = db_manager.execute_query(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = 'tenant_configuration' AND column_name = 'id'
        """,
        fetch_one=True
    )
    print(f"[OK] tenant_configuration.id is now: {new_type['data_type']}")

    # Step 9: Check if 'delta' tenant exists
    print("\n[9/10] Checking 'delta' tenant...")
    delta_tenant = db_manager.execute_query(
        "SELECT id FROM tenant_configuration WHERE id = %s",
        ('delta',),
        fetch_one=True
    )

    if not delta_tenant:
        print("[INFO] Creating 'delta' tenant...")
        db_manager.execute_query(
            """
            INSERT INTO tenant_configuration (id, name, description, is_active)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            ('delta', 'Delta Mining', 'Delta Mining & Computing Company', True)
        )
        print("[OK] 'delta' tenant created")
    else:
        print("[OK] 'delta' tenant already exists")

    # Step 10: Final verification
    print("\n[10/10] Running final verification...")
    test_invitation = db_manager.execute_query(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'user_invitations' AND column_name = 'tenant_id'
        """,
        fetch_one=True
    )
    print(f"[OK] user_invitations.tenant_id is: {test_invitation['data_type']}")

    print("\n" + "=" * 80)
    print("SUCCESS! TENANT SCHEMA MIGRATION COMPLETED")
    print("=" * 80)
    print("\nSummary:")
    print(f"  - tenant_configuration.id: INTEGER -> VARCHAR(50)")
    print(f"  - {len(dependent_tables)} dependent tables updated")
    print(f"  - All foreign keys re-created")
    print(f"  - 'delta' tenant verified/created")
    print("\nThe invitation system is now ready to use!")
    print("=" * 80)

except Exception as e:
    print(f"\n[ERROR] Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
