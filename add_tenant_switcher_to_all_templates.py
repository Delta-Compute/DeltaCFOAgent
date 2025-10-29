#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add tenant switcher to all templates that have Account Menu
"""
import sys
import io
import os
import re

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Templates that need tenant switcher (excluding business_overview.html and cfo_dashboard.html which are already done)
TEMPLATES = [
    'dashboard_advanced.html',
    'files.html',
    'invoices.html',
    'revenue.html',
    'whitelisted_accounts.html'
]

TENANT_SWITCHER_HTML = '''
                    <!-- Switch Tenant Section -->
                    <div id="tenantSwitcherSection" style="padding: 0.75rem 0.5rem; border-bottom: 1px solid #e2e8f0; display: none;">
                        <div style="padding: 0 0.5rem 0.5rem; font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">
                            Switch Tenant
                        </div>
                        <div id="tenantsList"></div>
                    </div>
'''

TENANT_SWITCHER_JS = '''
            // Load user tenants for switcher
            loadUserTenants();
        });

        // Load and display user's tenants
        async function loadUserTenants() {
            try {
                const user = auth.currentUser;
                if (!user) return;

                const idToken = await user.getIdToken();
                const response = await fetch('/api/auth/me', {
                    headers: { 'Authorization': `Bearer ${idToken}` }
                });

                const data = await response.json();

                if (data.success && data.tenants && data.tenants.length > 1) {
                    document.getElementById('tenantSwitcherSection').style.display = 'block';

                    const tenantsList = document.getElementById('tenantsList');
                    tenantsList.innerHTML = '';

                    data.tenants.forEach(tenant => {
                        const isActive = tenant.id === data.current_tenant?.id;
                        const tenantItem = document.createElement('button');
                        tenantItem.style.cssText = `
                            width: 100%;
                            text-align: left;
                            background: ${isActive ? '#e0f2fe' : 'transparent'};
                            border: none;
                            padding: 0.75rem 1rem;
                            cursor: pointer;
                            border-radius: 6px;
                            transition: background 0.2s;
                            margin-bottom: 0.25rem;
                        `;

                        tenantItem.innerHTML = `
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="flex: 1;">
                                    <div style="font-weight: ${isActive ? '600' : '500'}; color: #1e293b; font-size: 0.9rem;">
                                        ${tenant.company_name}
                                    </div>
                                    <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.15rem;">
                                        <span style="background: #f1f5f9; padding: 0.15rem 0.5rem; border-radius: 4px;">${tenant.role}</span>
                                    </div>
                                </div>
                                ${isActive ? '<div style="color: #0ea5e9; font-size: 1rem;">✓</div>' : ''}
                            </div>
                        `;

                        if (!isActive) {
                            tenantItem.onmouseover = () => { tenantItem.style.background = '#f1f5f9'; };
                            tenantItem.onmouseout = () => { tenantItem.style.background = 'transparent'; };
                            tenantItem.onclick = () => switchTenant(tenant.id);
                        }

                        tenantsList.appendChild(tenantItem);
                    });
                }
            } catch (error) {
                console.error('Error loading tenants:', error);
            }
        }

        // Switch to a different tenant
        async function switchTenant(tenantId) {
            try {
                const user = auth.currentUser;
                if (!user) return;

                const idToken = await user.getIdToken();
                const response = await fetch(`/api/auth/switch-tenant/${tenantId}`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${idToken}` }
                });

                const data = await response.json();

                if (data.success) {
                    window.location.reload();
                } else {
                    alert(data.message || 'Failed to switch tenant');
                }
            } catch (error) {
                console.error('Error switching tenant:', error);
                alert('Error switching tenant. Please try again.');
            }
        }
    </script>'''

def add_tenant_switcher_to_template(filepath):
    """Add tenant switcher HTML and JavaScript to a template"""
    print(f"\nProcessing: {os.path.basename(filepath)}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 1. Update dropdown min-width from 200px to 280px
    content = re.sub(
        r'min-width:\s*200px',
        'min-width: 280px',
        content
    )

    # 2. Add tenant switcher HTML after user info div
    # Find the pattern: user info div followed by menu items div
    pattern = r'(</div>\s*</div>\s*)(<!-- Switch Tenant Section -->.*?</div>\s*)?(\s*<div style="padding: 0\.5rem;">)'

    # Check if tenant switcher already exists
    if 'id="tenantSwitcherSection"' in content:
        print(f"  [OK] Tenant switcher HTML already exists")
    else:
        # Insert tenant switcher HTML
        replacement = r'\1' + TENANT_SWITCHER_HTML + r'\3'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        if content != original_content:
            print(f"  [OK] Added tenant switcher HTML")
            original_content = content
        else:
            print(f"  [ERROR] Could not find insertion point for tenant switcher HTML")

    # 3. Add tenant switcher JavaScript before closing script tag
    # Find where to insert: after logout button event listener, before closing });
    pattern = r'(logoutButton\?\.addEventListener\(.*?\}\);)\s*(\}\);)'

    if 'loadUserTenants()' in content:
        print(f"  [OK] Tenant switcher JS already exists")
    else:
        # Insert JS function call and functions
        replacement = r'\1\n' + TENANT_SWITCHER_JS
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        if content != original_content:
            print(f"  [OK] Added tenant switcher JavaScript")
        else:
            print(f"  [ERROR] Could not find insertion point for tenant switcher JS")

    # Write back if changed
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [SUCCESS] Template updated successfully")
        return True
    else:
        print(f"  [WARNING] No changes made")
        return False

def main():
    template_dir = os.path.join(os.path.dirname(__file__), 'web_ui', 'templates')

    print("=" * 80)
    print("ADDING TENANT SWITCHER TO ALL TEMPLATES")
    print("=" * 80)

    updated_count = 0
    for template_name in TEMPLATES:
        filepath = os.path.join(template_dir, template_name)
        if os.path.exists(filepath):
            if add_tenant_switcher_to_template(filepath):
                updated_count += 1
        else:
            print(f"\n[ERROR] File not found: {template_name}")

    print("\n" + "=" * 80)
    print(f"SUMMARY: Updated {updated_count}/{len(TEMPLATES)} templates")
    print("=" * 80)

if __name__ == '__main__':
    main()
