#!/usr/bin/env python3
"""
Script simples para testar se o PostgreSQL está funcionando no Cloud Run
"""
import requests
import json
import sys

SERVICE_URL = "https://deltacfoagent-620026562181.southamerica-east1.run.app"

def test_health_check():
    """Testar endpoint de health check"""
    print("🔍 Testing health check endpoint...")
    try:
        response = requests.get(f"{SERVICE_URL}/health", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check OK!")
            print(f"   Status: {data.get('status')}")
            print(f"   Database: {data.get('database')}")
            print(f"   Version: {data.get('version')}")

            if data.get('database') == 'PostgreSQL':
                print("🎉 SUCCESS: PostgreSQL is working!")
                return True
            else:
                print("⚠️  Still using SQLite, PostgreSQL not connected")
                return False
        else:
            print(f"❌ Health check failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check error: {e}")
        return False

def test_dashboard():
    """Testar se dashboard carrega"""
    print("\n🔍 Testing dashboard...")
    try:
        response = requests.get(SERVICE_URL, timeout=30)
        if response.status_code == 200:
            print("✅ Dashboard loads OK!")
            print(f"   Content length: {len(response.content)} bytes")
            return True
        else:
            print(f"❌ Dashboard failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Dashboard error: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 DELTA CFO AGENT - FINAL TEST")
    print("=" * 60)
    print(f"Testing service: {SERVICE_URL}")
    print()

    # Test health check
    health_ok = test_health_check()

    # Test dashboard
    dashboard_ok = test_dashboard()

    print("\n" + "=" * 60)
    if health_ok and dashboard_ok:
        print("🎉 ALL TESTS PASSED!")
        print("✅ PostgreSQL is working correctly!")
        print("✅ Dashboard is accessible!")
    else:
        print("⚠️  Some tests failed")
        if not health_ok:
            print("❌ Health check failed - PostgreSQL may not be connected")
        if not dashboard_ok:
            print("❌ Dashboard not accessible")

    print("=" * 60)
    return 0 if (health_ok and dashboard_ok) else 1

if __name__ == "__main__":
    sys.exit(main())