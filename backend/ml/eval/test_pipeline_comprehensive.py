#!/usr/bin/env python3
"""
Comprehensive Pipeline Test Suite

Tests the V2 pipeline end-to-end including:
- Detection accuracy
- Classification accuracy
- OCR boost effectiveness
- Response times
- Edge cases

Usage:
    python -m ml.eval.test_pipeline_comprehensive
"""

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Test configuration
API_BASE = "http://localhost:8001"
API_ENDPOINT = f"{API_BASE}/api/v1/ai/v2/recognize"


@dataclass
class TestResult:
    """Single test result."""
    test_name: str
    passed: bool
    expected: str
    actual: str
    confidence: float
    response_time_ms: float
    ocr_boosted: bool = False
    error: Optional[str] = None


@dataclass
class TestReport:
    """Complete test report."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    avg_response_time_ms: float = 0
    ocr_boost_count: int = 0
    results: List[TestResult] = field(default_factory=list)

    def add_result(self, result: TestResult):
        self.results.append(result)
        self.total_tests += 1
        if result.passed:
            self.passed += 1
        else:
            self.failed += 1
        if result.ocr_boosted:
            self.ocr_boost_count += 1

    def finalize(self):
        if self.results:
            self.avg_response_time_ms = sum(r.response_time_ms for r in self.results) / len(self.results)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total_tests if self.total_tests > 0 else 0


def check_server_health() -> bool:
    """Check if the server is running."""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def run_recognition_test(image_path: str) -> Dict:
    """Run recognition on an image and return results."""
    start_time = time.time()

    try:
        with open(image_path, 'rb') as f:
            files = {'image': (Path(image_path).name, f, 'image/jpeg')}
            response = requests.post(API_ENDPOINT, files=files, timeout=60)

        elapsed_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'data': data,
                'response_time_ms': elapsed_ms,
            }
        else:
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {response.text}",
                'response_time_ms': elapsed_ms,
            }
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return {
            'success': False,
            'error': str(e),
            'response_time_ms': elapsed_ms,
        }


def test_known_products(report: TestReport):
    """Test recognition of known products."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Known Products Recognition")
    logger.info("=" * 60)

    # Test cases: (image_path, expected_product, description)
    test_cases = [
        ("/Users/zver/Downloads/V99/training_photos/800.jpg", "Savoy Vodka", "Standard Savoy Vodka"),
        ("/Users/zver/Downloads/V99/training_photos/801.jpg", "Savoy Silver Vodka", "Savoy Silver (OCR variant)"),
    ]

    for image_path, expected, description in test_cases:
        if not Path(image_path).exists():
            logger.warning(f"  SKIP: {description} - Image not found")
            continue

        logger.info(f"\n  Testing: {description}")
        result = run_recognition_test(image_path)

        if result['success']:
            data = result['data']
            items = data.get('items', [])

            if items:
                item = items[0]
                actual = item.get('sku_name', 'Unknown')
                confidence = item.get('classification_confidence', 0)

                # Check if OCR boosted (would need to parse from response or logs)
                ocr_boosted = 'Silver' in actual and 'Silver' in expected

                passed = expected.lower() in actual.lower()

                test_result = TestResult(
                    test_name=description,
                    passed=passed,
                    expected=expected,
                    actual=actual,
                    confidence=confidence,
                    response_time_ms=result['response_time_ms'],
                    ocr_boosted=ocr_boosted,
                )

                status = "PASS" if passed else "FAIL"
                logger.info(f"    [{status}] Expected: {expected}, Got: {actual} ({confidence*100:.0f}%)")
                logger.info(f"    Response time: {result['response_time_ms']:.0f}ms")
            else:
                test_result = TestResult(
                    test_name=description,
                    passed=False,
                    expected=expected,
                    actual="No items detected",
                    confidence=0,
                    response_time_ms=result['response_time_ms'],
                )
                logger.info(f"    [FAIL] No items detected")
        else:
            test_result = TestResult(
                test_name=description,
                passed=False,
                expected=expected,
                actual="Error",
                confidence=0,
                response_time_ms=result['response_time_ms'],
                error=result.get('error'),
            )
            logger.info(f"    [FAIL] Error: {result.get('error')}")

        report.add_result(test_result)


def test_response_times(report: TestReport):
    """Test response time consistency."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Response Time Consistency")
    logger.info("=" * 60)

    image_path = "/Users/zver/Downloads/V99/training_photos/800.jpg"
    if not Path(image_path).exists():
        logger.warning("  SKIP: Test image not found")
        return

    times = []
    for i in range(3):
        result = run_recognition_test(image_path)
        if result['success']:
            times.append(result['response_time_ms'])
            logger.info(f"  Run {i+1}: {result['response_time_ms']:.0f}ms")

    if times:
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)

        logger.info(f"\n  Average: {avg_time:.0f}ms")
        logger.info(f"  Min: {min_time:.0f}ms, Max: {max_time:.0f}ms")

        # Pass if average is under 10 seconds and variance is reasonable
        passed = avg_time < 10000 and (max_time - min_time) < avg_time

        report.add_result(TestResult(
            test_name="Response Time Consistency",
            passed=passed,
            expected="<10s avg, low variance",
            actual=f"{avg_time:.0f}ms avg",
            confidence=1.0 if passed else 0.5,
            response_time_ms=avg_time,
        ))


def test_api_error_handling(report: TestReport):
    """Test API error handling."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: API Error Handling")
    logger.info("=" * 60)

    # Test 1: Invalid image data
    logger.info("\n  Testing: Invalid image data")
    try:
        response = requests.post(
            API_ENDPOINT,
            files={'image': ('test.jpg', b'invalid data', 'image/jpeg')},
            timeout=30
        )
        # Should return error, not crash
        passed = response.status_code in [400, 422, 500]
        logger.info(f"    [{'PASS' if passed else 'FAIL'}] Status: {response.status_code}")

        report.add_result(TestResult(
            test_name="Invalid image handling",
            passed=passed,
            expected="Error response (4xx/5xx)",
            actual=f"HTTP {response.status_code}",
            confidence=1.0 if passed else 0,
            response_time_ms=0,
        ))
    except Exception as e:
        logger.info(f"    [FAIL] Exception: {e}")
        report.add_result(TestResult(
            test_name="Invalid image handling",
            passed=False,
            expected="Error response",
            actual=f"Exception: {e}",
            confidence=0,
            response_time_ms=0,
            error=str(e),
        ))


def print_report(report: TestReport):
    """Print final test report."""
    report.finalize()

    logger.info("\n" + "=" * 60)
    logger.info("COMPREHENSIVE TEST REPORT")
    logger.info("=" * 60)
    logger.info(f"\nTimestamp: {report.timestamp}")
    logger.info(f"\nRESULTS:")
    logger.info(f"  Total Tests:    {report.total_tests}")
    logger.info(f"  Passed:         {report.passed}")
    logger.info(f"  Failed:         {report.failed}")
    logger.info(f"  Pass Rate:      {report.pass_rate*100:.1f}%")
    logger.info(f"  OCR Boosts:     {report.ocr_boost_count}")
    logger.info(f"  Avg Response:   {report.avg_response_time_ms:.0f}ms")

    if report.failed > 0:
        logger.info("\nFAILED TESTS:")
        for result in report.results:
            if not result.passed:
                logger.info(f"  - {result.test_name}")
                logger.info(f"    Expected: {result.expected}")
                logger.info(f"    Actual: {result.actual}")
                if result.error:
                    logger.info(f"    Error: {result.error}")

    logger.info("\n" + "=" * 60)
    status = "ALL TESTS PASSED" if report.failed == 0 else f"{report.failed} TESTS FAILED"
    logger.info(f"OVERALL: {status}")
    logger.info("=" * 60)

    return report.failed == 0


def main():
    """Run comprehensive tests."""
    logger.info("Starting Comprehensive Pipeline Tests")
    logger.info("=" * 60)

    # Check server
    logger.info("\nChecking server health...")
    if not check_server_health():
        # Try the recognize endpoint directly
        try:
            response = requests.get(f"{API_BASE}/docs", timeout=5)
            if response.status_code != 200:
                raise Exception("Server not responding")
        except:
            logger.error("Server is not running. Start with:")
            logger.error("  AI_V2_ENABLED=true uvicorn app.main:app --port 8001")
            sys.exit(1)

    logger.info("Server is running")

    # Run tests
    report = TestReport()

    test_known_products(report)
    test_response_times(report)
    test_api_error_handling(report)

    # Print report
    success = print_report(report)

    # Save report
    report_path = Path("logs/test_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report_data = {
        'timestamp': report.timestamp,
        'total_tests': report.total_tests,
        'passed': report.passed,
        'failed': report.failed,
        'pass_rate': report.pass_rate,
        'avg_response_time_ms': report.avg_response_time_ms,
        'ocr_boost_count': report.ocr_boost_count,
        'results': [
            {
                'test_name': r.test_name,
                'passed': r.passed,
                'expected': r.expected,
                'actual': r.actual,
                'confidence': r.confidence,
                'response_time_ms': r.response_time_ms,
                'ocr_boosted': r.ocr_boosted,
                'error': r.error,
            }
            for r in report.results
        ],
    }

    with open(report_path, 'w') as f:
        json.dump(report_data, f, indent=2)

    logger.info(f"\nReport saved to: {report_path}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
