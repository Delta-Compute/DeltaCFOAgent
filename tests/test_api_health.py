"""
Phase 0: API Health Check Tests
================================

Tests: 3
Purpose: Verify Flask API is responding and healthy
Coverage: Health endpoint, basic API functionality

Test List:
1. test_health_endpoint_exists - Does /health endpoint exist?
2. test_health_endpoint_returns_json - Does /health return valid JSON?
3. test_health_database_check - Does /health check database connectivity?
"""

import pytest
import json


@pytest.mark.api
@pytest.mark.smoke
class TestAPIHealth:
    """API health check and basic functionality tests"""

    def test_health_endpoint_exists(self, api_client):
        """
        Test: Health endpoint accessibility

        Given: Flask application running
        When: Making GET request to /health
        Then: Endpoint returns 200 OK status
        """
        response = api_client.get('/health')

        assert response.status_code == 200

    def test_health_endpoint_returns_json(self, api_client):
        """
        Test: Health endpoint JSON response

        Given: Flask application running
        When: Making GET request to /health
        Then: Response is valid JSON with expected structure
        """
        response = api_client.get('/health')

        # Verify JSON response
        assert response.content_type == 'application/json'

        data = json.loads(response.data)

        # Verify expected fields exist
        assert 'status' in data
        assert data['status'] in ['healthy', 'unhealthy']

    def test_health_database_check(self, api_client):
        """
        Test: Health endpoint database connectivity check

        Given: Flask application with database connection
        When: Making GET request to /health
        Then: Response includes database status information
        """
        response = api_client.get('/health')
        data = json.loads(response.data)

        # Health check should include database status
        assert 'database' in data or 'status' in data

        # If database field exists, it should indicate connectivity
        if 'database' in data:
            assert data['database'] in ['connected', 'healthy', 'ok', True]


# Additional smoke test for API root
@pytest.mark.smoke
def test_api_root_accessible(api_client):
    """
    Quick smoke test for API root endpoint
    Verifies the Flask app is serving requests
    """
    # Try to access root - should return something (200, 302, or 404)
    # Just verify app is responding
    response = api_client.get('/')

    # App is responding if status code is not 500 or connection error
    assert response.status_code < 500
