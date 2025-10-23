# Multi-Tenant System Test Suite

Comprehensive unit and integration tests for the DeltaCFOAgent multi-tenant system.

## Test Coverage

### 1. Tenant Configuration Tests (`test_tenant_config.py`)
Tests for `web_ui/tenant_config.py` - Configuration management functions

**Coverage:**
- ✅ Configuration caching (TTL validation, cache clearing)
- ✅ Tenant ID detection
- ✅ Configuration validation (entities, business context, categories, rules)
- ✅ Entity formatting for AI prompts
- ✅ Loading configurations from database
- ✅ Getting tenant entities, entity families, business context
- ✅ Getting accounting categories and pattern matching rules
- ✅ Updating configurations
- ✅ Convenience functions for current tenant

**Test Count:** ~50 tests

### 2. Industry Templates Tests (`test_industry_templates.py`)
Tests for `web_ui/industry_templates.py` - Industry template management

**Coverage:**
- ✅ Loading templates from JSON file
- ✅ Getting specific templates
- ✅ Listing available industries
- ✅ Customizing entity names with company name
- ✅ Applying templates to tenants
- ✅ Template preview generation
- ✅ Exporting templates as JSON
- ✅ Importing custom templates
- ✅ Getting recommended categories by industry

**Test Count:** ~30 tests

### 3. Multi-Tenant API Tests (`test_multi_tenant_api.py`)
Integration tests for API endpoints in `web_ui/app_db.py`

**Coverage:**
- ✅ GET/PUT `/api/tenant/config/<type>` - Configuration management
- ✅ GET `/api/tenant/industries` - List industries
- ✅ GET `/api/tenant/industries/<key>/preview` - Preview template
- ✅ POST `/api/tenant/industries/<key>/apply` - Apply template
- ✅ GET `/api/tenant/config/export` - Export configuration
- ✅ POST `/api/tenant/config/import` - Import configuration
- ✅ Error handling and validation

**Test Count:** ~25 tests

### 4. Dynamic Prompts Tests (`test_dynamic_prompts.py`)
Tests for `build_entity_classification_prompt()` - Dynamic AI prompt generation

**Coverage:**
- ✅ Prompt building for different industries (crypto, e-commerce, SaaS, services, general)
- ✅ Industry-specific context hints
- ✅ Multiple entities handling
- ✅ Explicit tenant ID usage
- ✅ Empty entities fallback
- ✅ Prompt structure validation (sections, instructions)

**Test Count:** ~20 tests

## Running Tests

### Run All Tests
```bash
# From the tests directory
python run_multi_tenant_tests.py

# Or from the project root
python tests/run_multi_tenant_tests.py
```

### Run Specific Test Module
```bash
# Run only tenant config tests
python run_multi_tenant_tests.py --module config

# Run only industry template tests
python run_multi_tenant_tests.py --module templates

# Run only API tests
python run_multi_tenant_tests.py --module api

# Run only dynamic prompt tests
python run_multi_tenant_tests.py --module prompts
```

### Run Individual Test Files
```bash
# Run a single test file directly
python test_tenant_config.py
python test_industry_templates.py
python test_multi_tenant_api.py
python test_dynamic_prompts.py
```

### Quiet Mode
```bash
# Reduce output verbosity
python run_multi_tenant_tests.py --quiet
```

## Test Output

### Sample Output
```
================================================================================
                    MULTI-TENANT SYSTEM TEST SUITE
================================================================================
Started: 2025-10-21 10:30:00
================================================================================

================================================================================
Running Tenant Configuration Tests...
================================================================================
test_cache_validation_expired ... ok
test_cache_validation_fresh ... ok
test_clear_specific_tenant_cache ... ok
...

Tenant Configuration Results:
  Tests Run: 50
  Passed: 50
  Failed: 0
  Errors: 0
  Duration: 2.45s
  Status: ✅ PASSED

================================================================================
                           OVERALL SUMMARY
================================================================================

Module Breakdown:
Module                         Tests    Passed   Failed   Errors   Status
--------------------------------------------------------------------------------
Tenant Configuration           50       50       0        0        ✅ PASS
Industry Templates             30       30       0        0        ✅ PASS
Multi-Tenant API               25       25       0        0        ✅ PASS
Dynamic Prompts                20       20       0        0        ✅ PASS
--------------------------------------------------------------------------------
TOTAL                          125      125      0        0

Total Tests Run: 125
Total Passed: 125 (100.0%)
Total Failed: 0
Total Errors: 0

🎉 ALL TESTS PASSED! 🎉
The multi-tenant system is working correctly.
```

## Test Architecture

### Mocking Strategy
Tests use `unittest.mock` to mock:
- Database connections (`db_manager`)
- File I/O operations (`builtins.open`)
- Tenant context functions
- Flask request/response objects

### Test Isolation
- Each test class has a `setUp()` method to reset state
- Cache is cleared between tenant config tests
- Flask test client is recreated for each API test
- No tests rely on external database or file system

### Fixtures
Tests use predefined mock data for:
- Entity configurations
- Business context
- Industry templates
- API request/response payloads

## Continuous Integration

### Adding to CI/CD Pipeline

**GitHub Actions Example:**
```yaml
name: Multi-Tenant Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run multi-tenant tests
        run: |
          python tests/run_multi_tenant_tests.py
```

**Jenkins Pipeline Example:**
```groovy
stage('Multi-Tenant Tests') {
    steps {
        sh 'python tests/run_multi_tenant_tests.py'
    }
}
```

## Code Coverage

To run tests with coverage:

```bash
# Install coverage
pip install coverage

# Run tests with coverage
coverage run tests/run_multi_tenant_tests.py

# Generate coverage report
coverage report

# Generate HTML coverage report
coverage html
```

Expected coverage:
- `tenant_config.py`: ~95%
- `industry_templates.py`: ~90%
- `build_entity_classification_prompt()`: ~95%
- API endpoints: ~85%

## Troubleshooting

### Import Errors
If you get import errors, make sure you're running from the project root or the tests directory:
```bash
cd /home/user/DeltaCFOAgent/tests
python run_multi_tenant_tests.py
```

### Module Not Found
Ensure the `web_ui` directory is in your Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:/home/user/DeltaCFOAgent/web_ui"
```

### Database Errors
Tests mock the database, so no actual database is required. If you see database errors:
1. Check that mocks are properly set up in the test
2. Ensure you're not accidentally connecting to a real database

## Contributing

### Adding New Tests

1. **Create test file** in `/tests/` directory:
   ```python
   #!/usr/bin/env python3
   import unittest
   from unittest.mock import Mock, patch

   class TestNewFeature(unittest.TestCase):
       def test_something(self):
           # Your test here
           pass
   ```

2. **Import in test runner** (`run_multi_tenant_tests.py`):
   ```python
   import test_new_feature

   test_modules = [
       # ... existing modules
       ('New Feature', test_new_feature),
   ]
   ```

3. **Run tests** to verify:
   ```bash
   python run_multi_tenant_tests.py
   ```

### Test Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `Test<FeatureName>`
- Test methods: `test_<what_it_tests>`

### Best Practices

1. **One assertion per test** when possible
2. **Clear test names** that describe what is being tested
3. **Mock external dependencies** (database, file I/O, network)
4. **Test both success and failure cases**
5. **Test edge cases** (empty lists, None values, etc.)

## Test Statistics

**Total Tests:** ~125
**Total Lines of Test Code:** ~1,800
**Code Coverage:** ~90%
**Average Test Duration:** <5 seconds

## Related Documentation

- [MULTI_TENANT_OVERHAUL_SUMMARY.md](../MULTI_TENANT_OVERHAUL_SUMMARY.md) - Implementation overview
- [tenant_config.py](../web_ui/tenant_config.py) - Configuration management
- [industry_templates.py](../web_ui/industry_templates.py) - Template management
- [app_db.py](../web_ui/app_db.py) - API endpoints

## Support

For questions or issues with tests:
1. Check test output for specific failure messages
2. Review the test file for the failing test
3. Ensure all dependencies are installed
4. Check that you're running from the correct directory
