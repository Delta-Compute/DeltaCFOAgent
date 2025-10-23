#!/usr/bin/env python3
"""
Multi-Tenant System Test Runner
Runs all unit and integration tests for the multi-tenant system
"""

import sys
import os
import unittest
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import test modules
import test_tenant_config
import test_industry_templates
import test_multi_tenant_api
import test_dynamic_prompts


def run_all_tests(verbose=True):
    """Run all multi-tenant system tests"""

    print("=" * 80)
    print(" " * 20 + "MULTI-TENANT SYSTEM TEST SUITE")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Test modules to run
    test_modules = [
        ('Tenant Configuration', test_tenant_config),
        ('Industry Templates', test_industry_templates),
        ('Multi-Tenant API', test_multi_tenant_api),
        ('Dynamic Prompts', test_dynamic_prompts)
    ]

    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0
    module_results = []

    # Run each test module
    for module_name, module in test_modules:
        print(f"\n{'=' * 80}")
        print(f"Running {module_name} Tests...")
        print(f"{'=' * 80}")

        start_time = time.time()

        # Load tests from module
        module_suite = loader.loadTestsFromModule(module)

        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(module_suite)

        # Calculate duration
        duration = time.time() - start_time

        # Collect stats
        tests_run = result.testsRun
        passed = tests_run - len(result.failures) - len(result.errors)
        failed = len(result.failures)
        errors = len(result.errors)

        total_tests += tests_run
        total_passed += passed
        total_failed += failed
        total_errors += errors

        module_results.append({
            'name': module_name,
            'tests_run': tests_run,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'duration': duration,
            'success': result.wasSuccessful()
        })

        print(f"\n{module_name} Results:")
        print(f"  Tests Run: {tests_run}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print(f"  Errors: {errors}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Status: {'✅ PASSED' if result.wasSuccessful() else '❌ FAILED'}")

    # Print overall summary
    print(f"\n{'=' * 80}")
    print(" " * 30 + "OVERALL SUMMARY")
    print(f"{'=' * 80}")

    # Print module breakdown
    print("\nModule Breakdown:")
    print(f"{'Module':<30} {'Tests':<8} {'Passed':<8} {'Failed':<8} {'Errors':<8} {'Status':<10}")
    print("-" * 80)
    for result in module_results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{result['name']:<30} {result['tests_run']:<8} {result['passed']:<8} "
              f"{result['failed']:<8} {result['errors']:<8} {status:<10}")

    # Print totals
    print("-" * 80)
    print(f"{'TOTAL':<30} {total_tests:<8} {total_passed:<8} {total_failed:<8} {total_errors:<8}")
    print()

    # Calculate success rate
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

    print(f"Total Tests Run: {total_tests}")
    print(f"Total Passed: {total_passed} ({success_rate:.1f}%)")
    print(f"Total Failed: {total_failed}")
    print(f"Total Errors: {total_errors}")

    # Overall status
    all_passed = all(r['success'] for r in module_results)
    print()
    if all_passed:
        print("🎉 ALL TESTS PASSED! 🎉")
        print("The multi-tenant system is working correctly.")
    else:
        print("❌ SOME TESTS FAILED")
        print("Please review the failures above.")

    print()
    print(f"{'=' * 80}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}")

    return all_passed


def run_specific_module(module_name, verbose=True):
    """Run tests for a specific module"""

    module_map = {
        'config': test_tenant_config,
        'templates': test_industry_templates,
        'api': test_multi_tenant_api,
        'prompts': test_dynamic_prompts
    }

    if module_name not in module_map:
        print(f"Error: Unknown module '{module_name}'")
        print(f"Available modules: {', '.join(module_map.keys())}")
        return False

    module = module_map[module_name]

    print(f"Running {module_name} tests...")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(module)

    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)

    return result.wasSuccessful()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Run multi-tenant system tests')
    parser.add_argument(
        '--module',
        choices=['all', 'config', 'templates', 'api', 'prompts'],
        default='all',
        help='Test module to run (default: all)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Reduce output verbosity'
    )

    args = parser.parse_args()

    verbose = not args.quiet

    if args.module == 'all':
        success = run_all_tests(verbose=verbose)
    else:
        success = run_specific_module(args.module, verbose=verbose)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
