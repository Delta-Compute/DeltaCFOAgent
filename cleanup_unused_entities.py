#!/usr/bin/env python3
"""
Remove business entities that exist in business_entities table but are not
used by any transactions. These are typically leftover from merge operations.
"""

import sys
sys.path.append('web_ui')

from database import db_manager

def cleanup_unused_entities(tenant_id):
    """Remove entities from business_entities that aren't used in transactions"""

    # Find entities in business_entities that aren't used in transactions
    query = """
    SELECT be.id, be.name, be.entity_type
    FROM business_entities be
    LEFT JOIN transactions t ON be.name = t.classified_entity AND be.tenant_id = t.tenant_id
    WHERE be.tenant_id = %s
    AND be.active = true
    AND t.classified_entity IS NULL
    ORDER BY be.name
    """

    unused_entities = db_manager.execute_query(query, (tenant_id,), fetch_all=True)

    if not unused_entities:
        print(f"✓ No unused entities found for tenant {tenant_id}")
        return

    print(f"\nFound {len(unused_entities)} unused entities in business_entities:")
    print("=" * 80)
    for entity in unused_entities:
        print(f"  • {entity['name']:<50} (type: {entity['entity_type']})")

    print("\n" + "=" * 80)
    print("These entities exist in business_entities but are NOT used by any transactions.")
    print("They were likely created during merges or data imports.")
    print("=" * 80)

    response = input(f"\nDelete these {len(unused_entities)} unused entities? (yes/no): ")

    if response.lower() not in ['yes', 'y']:
        print("Aborted.")
        return

    # Delete unused entities
    delete_query = """
    DELETE FROM business_entities
    WHERE tenant_id = %s AND id = %s
    """

    deleted = 0
    for entity in unused_entities:
        try:
            db_manager.execute_query(delete_query, (tenant_id, entity['id']))
            print(f"✓ Deleted: {entity['name']}")
            deleted += 1
        except Exception as e:
            print(f"✗ Failed to delete {entity['name']}: {e}")

    print("\n" + "=" * 80)
    print(f"✓ Successfully deleted {deleted}/{len(unused_entities)} entities")

    # Verify cleanup
    remaining = db_manager.execute_query("""
        SELECT COUNT(*) as count
        FROM business_entities be
        LEFT JOIN transactions t ON be.name = t.classified_entity AND be.tenant_id = t.tenant_id
        WHERE be.tenant_id = %s
        AND be.active = true
        AND t.classified_entity IS NULL
    """, (tenant_id,), fetch_one=True)

    if remaining['count'] == 0:
        print("\n✓ All unused entities have been cleaned up!")
    else:
        print(f"\n⚠ Warning: {remaining['count']} unused entities still remain")

if __name__ == '__main__':
    print("Unused Entity Cleanup")
    print("=" * 80)

    tenant_id = input("Enter tenant ID (default: delta): ").strip() or 'delta'
    cleanup_unused_entities(tenant_id)
