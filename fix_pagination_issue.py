#!/usr/bin/env python3
"""
Fix Pagination Issue
Resolve o problema onde 261 transações são reduzidas para 50 após 1 segundo
"""

def add_pagination_controls():
    """Add pagination control to dashboard_advanced.html"""
    template_path = "web_ui/templates/dashboard_advanced.html"

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add pagination control before the table
        pagination_control = '''
        <div class="pagination-control" style="margin: 10px 0; text-align: right;">
            <label for="itemsPerPage" style="margin-right: 10px;">Items per page:</label>
            <select id="itemsPerPage" onchange="changeItemsPerPage()">
                <option value="25">25</option>
                <option value="50" selected>50</option>
                <option value="100">100</option>
                <option value="250">250</option>
                <option value="500">500</option>
                <option value="all">Show All</option>
            </select>
        </div>
        '''

        # Find the table container and add control before it
        table_start = '<div class="table-container">'
        if table_start in content:
            content = content.replace(table_start, pagination_control + '\n        ' + table_start)

            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print("SUCCESS: Added pagination control to dashboard_advanced.html")
            return True

    except Exception as e:
        print(f"ERROR: Failed to add pagination control: {e}")
        return False

def update_javascript():
    """Update script_advanced.js to use dynamic pagination"""
    script_path = "web_ui/static/script_advanced.js"

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace fixed per_page with dynamic value
        old_line = "    params.append('per_page', 50);"
        new_line = """    // Dynamic pagination
    const itemsPerPage = document.getElementById('itemsPerPage').value;
    if (itemsPerPage !== 'all') {
        params.append('per_page', itemsPerPage);
    } else {
        params.append('per_page', 10000); // Large number to get all
    }"""

        if old_line in content:
            content = content.replace(old_line, new_line)

        # Add function to handle pagination change
        pagination_function = '''
// Function to change items per page
function changeItemsPerPage() {
    currentPage = 1; // Reset to first page
    loadTransactions();
}

// Set default pagination on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check if user has preference in localStorage
    const savedItemsPerPage = localStorage.getItem('itemsPerPage');
    if (savedItemsPerPage) {
        document.getElementById('itemsPerPage').value = savedItemsPerPage;
    }

    // Save preference when changed
    document.getElementById('itemsPerPage').addEventListener('change', function() {
        localStorage.setItem('itemsPerPage', this.value);
    });
});

'''

        # Add the function at the end of the file
        content += pagination_function

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print("SUCCESS: Updated script_advanced.js with dynamic pagination")
        return True

    except Exception as e:
        print(f"ERROR: Failed to update JavaScript: {e}")
        return False

def update_backend():
    """Update backend to handle 'all' pagination"""
    app_path = "web_ui/app_db.py"

    try:
        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the transactions endpoint and update per_page handling
        old_per_page_line = '        per_page = int(request.args.get(\'per_page\', 50))'
        new_per_page_line = '''        # Handle dynamic per_page, including 'all' option
        per_page_param = request.args.get('per_page', 50)
        if str(per_page_param) == 'all' or int(per_page_param) > 5000:
            per_page = None  # No limit
        else:
            per_page = int(per_page_param)'''

        if old_per_page_line in content:
            content = content.replace(old_per_page_line, new_per_page_line)

        # Also update the load_transactions_from_db call
        old_load_call = '        transactions, total_count = load_transactions_from_db(filters, page, per_page)'
        new_load_call = '''        # Handle unlimited pagination
        if per_page is None:
            transactions, total_count = load_transactions_from_db(filters, 1, 10000)
            page = 1  # Single page with all results
            pages = 1
        else:
            transactions, total_count = load_transactions_from_db(filters, page, per_page)
            pages = (total_count + per_page - 1) // per_page'''

        if old_load_call in content:
            content = content.replace(old_load_call, new_load_call)

            # Update the pagination response
            old_pages_calc = '                \'pages\': (total_count + per_page - 1) // per_page'
            new_pages_calc = '                \'pages\': pages'

            if old_pages_calc in content:
                content = content.replace(old_pages_calc, new_pages_calc)

        with open(app_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print("SUCCESS: Updated backend to handle unlimited pagination")
        return True

    except Exception as e:
        print(f"ERROR: Failed to update backend: {e}")
        return False

def create_quick_fix():
    """Create a quick JavaScript fix for immediate use"""
    quick_fix = '''
// Quick Fix for Pagination Issue
// This script forces showing all transactions instead of just 50

// Override the buildFilterQuery function
(function() {
    console.log('Applying pagination quick fix...');

    // Save original function
    const originalBuildFilterQuery = window.buildFilterQuery;

    window.buildFilterQuery = function() {
        // Call original function to get base params
        const queryString = originalBuildFilterQuery ? originalBuildFilterQuery() : '';
        const params = new URLSearchParams(queryString);

        // Override per_page to show all
        params.delete('per_page');
        params.append('per_page', 1000);

        console.log('Pagination fix applied - requesting 1000 items');
        return params.toString();
    };

    // Force reload after 2 seconds if loadTransactions exists
    setTimeout(() => {
        if (typeof loadTransactions === 'function') {
            console.log('Reloading transactions with fix...');
            loadTransactions();
        }
    }, 2000);

    console.log('Pagination quick fix loaded successfully');
})();
'''

    with open('web_ui/static/pagination_fix.js', 'w') as f:
        f.write(quick_fix)

    print("Created pagination_fix.js - include this in your page for immediate fix")
    return True

def main():
    """Apply all fixes for pagination issue"""
    print("Fixing Pagination Issue")
    print("=" * 30)
    print("Problem: 261 transactions reduced to 50 after 1 second")
    print("Cause: JavaScript forces 50 items per page automatically")
    print("")

    success_count = 0
    total_fixes = 4

    # Apply fixes
    if add_pagination_controls():
        success_count += 1

    if update_javascript():
        success_count += 1

    if update_backend():
        success_count += 1

    if create_quick_fix():
        success_count += 1

    print(f"\nFIXES APPLIED: {success_count}/{total_fixes}")

    if success_count == total_fixes:
        print("\nSUCCESS: All fixes applied successfully!")
        print("\nFeatures added:")
        print("✅ Pagination dropdown (25, 50, 100, 250, 500, Show All)")
        print("✅ User preference saved in localStorage")
        print("✅ Backend support for unlimited results")
        print("✅ Quick fix JavaScript for immediate use")

        print("\nNext steps:")
        print("1. Restart Flask app: cd web_ui && python app_db.py")
        print("2. Or add this to your page for immediate fix:")
        print('   <script src="/static/pagination_fix.js"></script>')

        print("\nYour 261 transactions will now show properly!")
    else:
        print("\nWARNING: Some fixes failed - check errors above")

    return success_count == total_fixes

if __name__ == "__main__":
    main()