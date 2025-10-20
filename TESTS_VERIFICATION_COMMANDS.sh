#!/bin/bash
# Tests Audit Verification Commands
# Run these to reproduce the audit findings

echo "=========================================="
echo "DemeterAI v2.0 - Test Audit Verification"
echo "=========================================="
echo ""

# 1. Run all tests and get summary
echo "1. Running ALL tests (excluding benchmarks)..."
pytest tests/ -v --tb=short --no-cov -m "not benchmark" -q

# Capture exit code
TEST_EXIT_CODE=$?
echo ""
echo "Exit Code: $TEST_EXIT_CODE"
echo ""

# 2. Get coverage report
echo "2. Running coverage analysis..."
pytest tests/ --cov=app --cov-report=term --cov-report=json -m "not benchmark" -q
echo ""

# 3. Extract overall coverage
echo "3. Overall coverage percentage:"
python3 -c "import json; data = json.load(open('coverage.json')); print(f\"Total Coverage: {data['totals']['percent_covered']:.2f}%\")"
echo ""

# 4. Count tests by category
echo "4. Test counts by category:"
echo ""
echo "Unit Tests - Models:"
pytest tests/unit/models/ -v --tb=no --no-cov -q 2>&1 | tail -1
echo ""

echo "Unit Tests - Services:"
pytest tests/unit/services/ -v --tb=no --no-cov -q 2>&1 | tail -1
echo ""

echo "Unit Tests - Repositories:"
pytest tests/unit/repositories/ -v --tb=no --no-cov -q 2>&1 | tail -1
echo ""

echo "Integration Tests:"
pytest tests/integration/ -v --tb=no --no-cov -m "not benchmark" -q 2>&1 | tail -1
echo ""

# 5. Specific failing test examples
echo "5. Example failing tests:"
echo ""

echo "a) ProductSize code validation (test structure issue):"
pytest tests/unit/models/test_product_size.py::TestProductSizeCodeValidation::test_code_valid_uppercase -v --tb=short --no-cov
echo ""

echo "b) Warehouse enum validation (model doesn't validate at Python level):"
pytest tests/unit/models/test_warehouse.py::TestWarehouseTypeEnum::test_warehouse_type_enum_invalid_values -v --tb=short --no-cov
echo ""

echo "c) MLPipelineCoordinator signature mismatch (parameter names wrong):"
pytest tests/unit/services/ml_processing/test_pipeline_coordinator.py::TestMLPipelineCoordinatorHappyPath::test_process_complete_pipeline_success -v --tb=short --no-cov
echo ""

echo "d) ML Band Estimation accuracy (algorithm issue):"
pytest tests/integration/ml_processing/test_band_estimation_integration.py::TestBandEstimationAccuracy::test_estimation_accuracy_within_10_percent -v --tb=short --no-cov
echo ""

# 6. Check for test anti-patterns
echo "6. Checking for test anti-patterns:"
echo ""

echo "a) Tests with 'assert True' (always pass):"
grep -r "assert True" tests/ --include="*.py" | grep -v "__pycache__"
echo ""

echo "b) Mock usage in integration tests:"
grep -r "Mock\|mock" tests/integration/ --include="*.py" | wc -l
echo " instances found in integration tests (should be 0)"
echo ""

echo "c) Self-documented bugs in tests:"
grep -rn "NOTE:.*fail\|FIXME\|TODO.*fail" tests/ --include="*.py" | grep -v "__pycache__"
echo ""

# 7. Coverage by module type
echo "7. Coverage breakdown by module:"
echo ""
pytest tests/ --cov=app.models --cov-report=term -m "not benchmark" -q 2>&1 | grep "TOTAL"
pytest tests/ --cov=app.repositories --cov-report=term -m "not benchmark" -q 2>&1 | grep "TOTAL"
pytest tests/ --cov=app.services --cov-report=term -m "not benchmark" -q 2>&1 | grep "TOTAL"
pytest tests/ --cov=app.schemas --cov-report=term -m "not benchmark" -q 2>&1 | grep "TOTAL"
pytest tests/ --cov=app.core --cov-report=term -m "not benchmark" -q 2>&1 | grep "TOTAL"
echo ""

# 8. File counts
echo "8. Test file statistics:"
echo ""
echo "Total test files: $(find tests/ -name "*.py" -type f ! -path "*__pycache__*" | wc -l)"
echo "Unit test files: $(find tests/unit -name "*.py" -type f ! -path "*__pycache__*" | wc -l)"
echo "Integration test files: $(find tests/integration -name "*.py" -type f ! -path "*__pycache__*" | wc -l)"
echo ""

# 9. Database connection verification
echo "9. Database connection verification:"
echo ""
docker ps | grep demeterai-db-test || echo "WARNING: Test database container not running!"
echo ""

# Summary
echo "=========================================="
echo "VERIFICATION COMPLETE"
echo "=========================================="
echo ""
echo "Key Findings:"
echo "- Exit Code: $TEST_EXIT_CODE (0=pass, non-zero=fail)"
echo "- See coverage.json for detailed coverage data"
echo "- See TESTS_AUDIT_REPORT.md for full analysis"
echo "- See TESTS_QUICK_SUMMARY.md for quick reference"
echo ""
