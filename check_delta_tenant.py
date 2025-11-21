#!/usr/bin/env python3
"""Quick script to check Delta tenant configuration"""

from web_ui.database import db_manager

# Check tenant configuration
print("=== DELTA TENANT CONFIGURATION ===")
tenant_config = db_manager.execute_query("""
    SELECT company_name, company_tagline, company_description,
           industry, default_currency, headquarters_location,
           website_url, contact_email
    FROM tenant_configuration
    WHERE tenant_id = %s
""", ('delta',), fetch_one=True)

if tenant_config:
    print("\nTenant Config:")
    for key, value in dict(tenant_config).items():
        print(f"  {key}: {value}")
else:
    print("  No tenant configuration found!")

# Check business entities
print("\n=== BUSINESS ENTITIES ===")
entities = db_manager.execute_query("""
    SELECT name, description, entity_type, active
    FROM business_entities
    WHERE tenant_id = %s
    ORDER BY name
""", ('delta',), fetch_all=True)

if entities:
    print(f"\nFound {len(entities)} business entities:")
    for entity in entities:
        e = dict(entity)
        print(f"  - {e['name']}: {e['entity_type']} (active: {e['active']})")
else:
    print("  No business entities found!")

# Calculate completion percentage
print("\n=== ONBOARDING STATUS ===")
required_fields = ['company_name', 'company_tagline', 'company_description', 'industry']
optional_fields = ['headquarters_location', 'website_url', 'contact_email']

filled_required = 0
filled_optional = 0

if tenant_config:
    config = dict(tenant_config)
    for field in required_fields:
        if config.get(field):
            filled_required += 1
    for field in optional_fields:
        if config.get(field):
            filled_optional += 1

total_fields = len(required_fields) + len(optional_fields)
filled_fields = filled_required + filled_optional
completion = int((filled_fields / total_fields) * 100)

print(f"  Required fields filled: {filled_required}/{len(required_fields)}")
print(f"  Optional fields filled: {filled_optional}/{len(optional_fields)}")
print(f"  Overall completion: {completion}%")
print(f"  Has entities: {len(entities) > 0 if entities else False}")
print(f"  Should show 'Welcome Back' mode: {completion >= 90 and entities and len(entities) > 0}")
