#!/usr/bin/env python3
"""
Fix all tenant_configuration queries across the codebase
Changes tc.tenant_id to tc.id and tc.company_description to tc.description
"""
import os
import re

FILES_TO_FIX = [
    'api/auth_routes.py',
    'api/cfo_routes.py',
    'api/tenant_routes.py',
    'web_ui/app_db.py',
    'add_user_to_tenant.py'
]

def fix_file(filepath):
    """Fix tenant queries in a file"""
    if not os.path.exists(filepath):
        print(f"SKIP: {filepath} (not found)")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    changes_made = []

    # Fix 1: tc.tenant_id -> tc.id (when selecting)
    pattern1 = r'tc\.tenant_id(?=[\s,])'
    if re.search(pattern1, content):
        content = re.sub(pattern1, 'tc.id', content)
        changes_made.append("tc.tenant_id -> tc.id")

    # Fix 2: JOIN ... ON tu.tenant_id = tc.tenant_id -> tc.id
    pattern2 = r'ON\s+tu\.tenant_id\s*=\s*tc\.tenant_id'
    if re.search(pattern2, content, re.IGNORECASE):
        content = re.sub(pattern2, 'ON tu.tenant_id = tc.id', content, flags=re.IGNORECASE)
        changes_made.append("JOIN ... tc.tenant_id -> tc.id")

    # Fix 3: JOIN ... ON ui.tenant_id = tc.tenant_id -> tc.id
    pattern3 = r'ON\s+ui\.tenant_id\s*=\s*tc\.tenant_id'
    if re.search(pattern3, content, re.IGNORECASE):
        content = re.sub(pattern3, 'ON ui.tenant_id = tc.id', content, flags=re.IGNORECASE)
        changes_made.append("JOIN ... ui.tenant_id = tc.id")

    # Fix 4: JOIN ... ON tc.tenant_id = tu.tenant_id -> tc.id = tu.tenant_id
    pattern4 = r'ON\s+tc\.tenant_id\s*=\s*tu\.tenant_id'
    if re.search(pattern4, content, re.IGNORECASE):
        content = re.sub(pattern4, 'ON tc.id = tu.tenant_id', content, flags=re.IGNORECASE)
        changes_made.append("JOIN ... tc.tenant_id = tu.tenant_id -> tc.id")

    # Fix 5: tc.company_description -> tc.description
    pattern5 = r'tc\.company_description'
    if re.search(pattern5, content):
        content = re.sub(pattern5, 'tc.description', content)
        changes_made.append("tc.company_description -> tc.description")

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"FIXED: {filepath}")
        for change in changes_made:
            print(f"  - {change}")
        return True
    else:
        print(f"OK: {filepath} (no changes needed)")
        return False

def main():
    """Fix all files"""
    print("\n" + "="*80)
    print("Fixing tenant_configuration queries across codebase")
    print("="*80 + "\n")

    fixed_count = 0
    for filepath in FILES_TO_FIX:
        if fix_file(filepath):
            fixed_count += 1
        print()

    print("="*80)
    print(f"Fixed {fixed_count} file(s)")
    print("="*80 + "\n")

    print("IMPORTANT: Restart the Flask server to apply changes!")
    print("  cd web_ui")
    print("  python app_db.py")
    print()

if __name__ == "__main__":
    main()
