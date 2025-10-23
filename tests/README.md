# DeltaCFOAgent Test Suite

## Phase 0: Minimal Viable Test Suite

Welcome to the DeltaCFOAgent test suite! We're following an **incremental testing approach** - starting small and building up gradually.

### Current Status

**Phase:** Phase 0 - Foundation
**Tests:** 8 total (5 database + 3 API)
**Coverage:** ~15%
**Execution Time:** <30 seconds

### Quick Start

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=. --cov-report=term

# Run only smoke tests (fastest)
pytest -m smoke

# Run only database tests
pytest -m database

# Run only API tests
pytest -m api
```

### Test Organization

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── test_database_basic.py         # 5 database tests
└── test_api_health.py             # 3 API health tests
```

### What's Tested (Phase 0)

✅ **Database Tests:**
- Connection establishment
- Query execution
- Insert operations
- Transaction rollback
- Connection pooling

✅ **API Tests:**
- Health endpoint existence
- JSON response format
- Database connectivity check

### Test Markers

Use markers to run specific test categories:

```bash
pytest -m smoke       # Critical path tests only
pytest -m database    # Database tests only
pytest -m api         # API tests only
pytest -m unit        # Unit tests only
pytest -m integration # Integration tests only
```

### Expected Output

```bash
$ pytest -v

tests/test_database_basic.py::TestDatabaseBasic::test_database_connection PASSED
tests/test_database_basic.py::TestDatabaseBasic::test_database_query_execution PASSED
tests/test_database_basic.py::TestDatabaseBasic::test_database_insert_operation PASSED
tests/test_database_basic.py::TestDatabaseBasic::test_database_transaction_rollback PASSED
tests/test_database_basic.py::TestDatabaseBasic::test_connection_pool_exists PASSED
tests/test_database_basic.py::test_database_health_check PASSED
tests/test_api_health.py::TestAPIHealth::test_health_endpoint_exists PASSED
tests/test_api_health.py::TestAPIHealth::test_health_endpoint_returns_json PASSED
tests/test_api_health.py::TestAPIHealth::test_health_database_check PASSED

========== 9 passed in 2.5s ==========
```

### Environment Variables

Tests use these environment variables (set automatically by `conftest.py`):

- `DB_TYPE` - Database type (postgresql)
- `DB_HOST` - Database host
- `DB_PORT` - Database port
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password

For custom test database, prefix with `TEST_`:
- `TEST_DB_NAME`
- `TEST_DB_HOST`
- etc.

### CI/CD Integration

Tests run automatically in GitHub Actions on:
- Every push to any branch
- Every pull request

See `.github/workflows/tests.yml` for configuration.

### Next Steps

See `INCREMENTAL_TESTING_ROADMAP.md` for the complete testing roadmap.

**Phase 1 (Next):** Add CRUD tests for transactions (10 tests)
**Phase 2:** Add smart ingestion tests (5 tests)
**Phase 3:** Add API endpoint tests (12 tests)

### Writing New Tests

Follow this pattern:

```python
import pytest

@pytest.mark.unit  # or integration, api, database
class TestFeatureName:
    """Test suite for FeatureName"""

    def test_specific_behavior(self, fixture_name):
        """
        Test: What you're testing

        Given: Initial state
        When: Action performed
        Then: Expected result
        """
        # Arrange
        setup_code()

        # Act
        result = function_under_test()

        # Assert
        assert result == expected_value
```

### Troubleshooting

**Tests fail with database connection error:**
- Check that PostgreSQL is running
- Verify database credentials in `.env`
- Ensure `delta_cfo` database exists

**Import errors:**
- Run `pip install -r requirements-test.txt`
- Ensure you're in the project root directory

**Tests hang:**
- Check for infinite loops or blocking operations
- Verify database isn't locked
- Kill any hanging processes: `ps aux | grep pytest`

### Getting Help

- Read the full plan: `TESTING_PLAN.md`
- Check the roadmap: `INCREMENTAL_TESTING_ROADMAP.md`
- Review test patterns in existing tests
- Ask the team!

---

**Phase 0 Complete!** Ready for Phase 1 🚀
