#!/usr/bin/env python3
"""
Migration script to add Spanish language support to the database.
Extends the existing bilingual (en/pt) support to trilingual (en/pt/es).

Usage:
    python migrations/apply_spanish_language_migration.py
    python migrations/apply_spanish_language_migration.py --dry-run
    python migrations/apply_spanish_language_migration.py --verify
"""

import os
import sys
import argparse

# Add parent directory to path to import database module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_ui.database import db_manager


def check_current_constraints():
    """Check current state of language constraints."""
    query = """
    SELECT conname, pg_get_constraintdef(oid) as definition
    FROM pg_constraint
    WHERE conname IN ('chk_users_language', 'chk_tenant_language')
    """
    try:
        results = db_manager.execute_query(query)
        return results
    except Exception as e:
        print(f"Error checking constraints: {e}")
        return []


def verify_spanish_support():
    """Verify that Spanish language is supported in the constraints."""
    constraints = check_current_constraints()

    if not constraints:
        print("No language constraints found.")
        return False

    all_support_spanish = True
    for constraint in constraints:
        name = constraint.get('conname', '')
        definition = constraint.get('definition', '')
        supports_spanish = "'es'" in definition

        print(f"  {name}: {'Supports Spanish' if supports_spanish else 'Does NOT support Spanish'}")
        print(f"    Definition: {definition}")

        if not supports_spanish:
            all_support_spanish = False

    return all_support_spanish


def apply_migration(dry_run=False):
    """Apply the Spanish language migration."""
    migration_sql_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'add_spanish_language.sql'
    )

    if not os.path.exists(migration_sql_path):
        print(f"Error: Migration SQL file not found: {migration_sql_path}")
        return False

    with open(migration_sql_path, 'r') as f:
        migration_sql = f.read()

    if dry_run:
        print("\n=== DRY RUN - SQL to be executed ===")
        print(migration_sql)
        print("=== END DRY RUN ===\n")
        return True

    print("Applying Spanish language migration...")

    try:
        # Execute the migration
        # Split by the DO $$ blocks and execute each statement
        statements = []
        current_statement = []
        in_do_block = False

        for line in migration_sql.split('\n'):
            stripped = line.strip()

            # Track DO $$ blocks
            if stripped.startswith('DO $$'):
                in_do_block = True

            current_statement.append(line)

            if in_do_block and stripped == 'END $$;':
                in_do_block = False
                statements.append('\n'.join(current_statement))
                current_statement = []
            elif not in_do_block and stripped.endswith(';') and not stripped.startswith('--'):
                statements.append('\n'.join(current_statement))
                current_statement = []

        # Execute each statement
        for i, stmt in enumerate(statements):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                try:
                    db_manager.execute_query(stmt)
                    print(f"  Statement {i+1}: OK")
                except Exception as e:
                    print(f"  Statement {i+1}: Error - {e}")
                    # Continue with other statements

        print("Migration applied successfully!")
        return True

    except Exception as e:
        print(f"Error applying migration: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Apply Spanish language migration')
    parser.add_argument('--dry-run', action='store_true', help='Show SQL without executing')
    parser.add_argument('--verify', action='store_true', help='Verify current state only')
    args = parser.parse_args()

    print("=" * 60)
    print("Spanish Language Migration Tool")
    print("=" * 60)

    print("\n1. Checking current constraint state...")
    constraints = check_current_constraints()

    if constraints:
        print(f"   Found {len(constraints)} language constraint(s):")
        for c in constraints:
            print(f"   - {c.get('conname')}: {c.get('definition', 'N/A')}")
    else:
        print("   No language constraints found (may need to run language preferences migration first)")

    if args.verify:
        print("\n2. Verifying Spanish support...")
        if verify_spanish_support():
            print("\n   Spanish language support is already enabled!")
        else:
            print("\n   Spanish language support is NOT enabled. Run migration to add it.")
        return

    # Check if migration is needed
    supports_spanish = verify_spanish_support()

    if supports_spanish and not args.dry_run:
        print("\n   Spanish support already enabled. No migration needed.")
        return

    print("\n2. Applying migration...")
    success = apply_migration(dry_run=args.dry_run)

    if success and not args.dry_run:
        print("\n3. Verifying migration...")
        if verify_spanish_support():
            print("\n   Migration verified successfully!")
        else:
            print("\n   Warning: Migration may not have applied correctly.")

    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
