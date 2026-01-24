"""
AI Pipeline Monitoring Service

Tracks and reports metrics for the AI recognition pipeline:
- Request counts and throughput
- Response times (p50, p95, p99)
- Classification confidence distribution
- OCR boost effectiveness
- Error rates and types

Usage:
    from app.services.ai.monitoring import ai_monitor

    # Record a recognition request
    ai_monitor.record_request(
        response_time_ms=1500,
        items_detected=2,
        ocr_boosted=1,
        confidence_scores=[0.92, 0.85],
    )

    # Get metrics
    metrics = ai_monitor.get_metrics()
"""

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    timestamp: float
    response_time_ms: float
    items_detected: int
    ocr_boosted: int
    confidence_scores: List[float]
    success: bool
    error_type: Optional[str] = None


class AIMonitor:
    """Singleton monitor for AI pipeline metrics."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Keep last 1000 requests for metrics
        self._max_history = 1000
        self._requests: deque[RequestMetrics] = deque(maxlen=self._max_history)

        # Counters (all-time)
        self._total_requests = 0
        self._total_errors = 0
        self._total_items_detected = 0
        self._total_ocr_boosts = 0

        # Start time for uptime tracking
        self._start_time = time.time()

        self._initialized = True
        logger.info("AI Monitor initialized")

    def record_request(
        self,
        response_time_ms: float,
        items_detected: int = 0,
        ocr_boosted: int = 0,
        confidence_scores: Optional[List[float]] = None,
        success: bool = True,
        error_type: Optional[str] = None,
    ):
        """Record metrics for a recognition request."""
        metrics = RequestMetrics(
            timestamp=time.time(),
            response_time_ms=response_time_ms,
            items_detected=items_detected,
            ocr_boosted=ocr_boosted,
            confidence_scores=confidence_scores or [],
            success=success,
            error_type=error_type,
        )

        self._requests.append(metrics)
        self._total_requests += 1
        self._total_items_detected += items_detected
        self._total_ocr_boosts += ocr_boosted

        if not success:
            self._total_errors += 1

        # Log slow requests
        if response_time_ms > 5000:
            logger.warning(f"Slow request: {response_time_ms:.0f}ms")

    def record_error(self, error_type: str, response_time_ms: float = 0):
        """Record an error."""
        self.record_request(
            response_time_ms=response_time_ms,
            success=False,
            error_type=error_type,
        )

    def get_metrics(self, window_minutes: int = 60) -> Dict:
        """Get current metrics summary."""
        now = time.time()
        window_start = now - (window_minutes * 60)

        # Filter to window
        recent = [r for r in self._requests if r.timestamp >= window_start]

        if not recent:
            return self._empty_metrics()

        # Calculate response time percentiles
        response_times = sorted([r.response_time_ms for r in recent])
        p50_idx = int(len(response_times) * 0.50)
        p95_idx = int(len(response_times) * 0.95)
        p99_idx = int(len(response_times) * 0.99)

        # Confidence distribution
        all_confidences = []
        for r in recent:
            all_confidences.extend(r.confidence_scores)

        conf_dist = self._confidence_distribution(all_confidences)

        # Error breakdown
        errors = [r for r in recent if not r.success]
        error_types = {}
        for e in errors:
            error_types[e.error_type or 'unknown'] = error_types.get(e.error_type or 'unknown', 0) + 1

        return {
            'window_minutes': window_minutes,
            'uptime_seconds': int(now - self._start_time),

            # Request counts
            'total_requests': self._total_requests,
            'window_requests': len(recent),
            'requests_per_minute': len(recent) / window_minutes if window_minutes > 0 else 0,

            # Response times
            'response_time': {
                'avg_ms': sum(response_times) / len(response_times),
                'p50_ms': response_times[p50_idx] if response_times else 0,
                'p95_ms': response_times[min(p95_idx, len(response_times)-1)] if response_times else 0,
                'p99_ms': response_times[min(p99_idx, len(response_times)-1)] if response_times else 0,
                'min_ms': min(response_times) if response_times else 0,
                'max_ms': max(response_times) if response_times else 0,
            },

            # Detection stats
            'detection': {
                'total_items': self._total_items_detected,
                'window_items': sum(r.items_detected for r in recent),
                'avg_items_per_request': sum(r.items_detected for r in recent) / len(recent),
            },

            # OCR stats
            'ocr': {
                'total_boosts': self._total_ocr_boosts,
                'window_boosts': sum(r.ocr_boosted for r in recent),
                'boost_rate': sum(r.ocr_boosted for r in recent) / len(recent) if recent else 0,
            },

            # Confidence distribution
            'confidence': conf_dist,

            # Error stats
            'errors': {
                'total': self._total_errors,
                'window': len(errors),
                'rate': len(errors) / len(recent) if recent else 0,
                'by_type': error_types,
            },
        }

    def _confidence_distribution(self, confidences: List[float]) -> Dict:
        """Calculate confidence score distribution."""
        if not confidences:
            return {
                'avg': 0,
                'min': 0,
                'max': 0,
                'above_90': 0,
                'above_80': 0,
                'above_70': 0,
                'below_70': 0,
            }

        return {
            'avg': sum(confidences) / len(confidences),
            'min': min(confidences),
            'max': max(confidences),
            'above_90': sum(1 for c in confidences if c >= 0.90) / len(confidences),
            'above_80': sum(1 for c in confidences if c >= 0.80) / len(confidences),
            'above_70': sum(1 for c in confidences if c >= 0.70) / len(confidences),
            'below_70': sum(1 for c in confidences if c < 0.70) / len(confidences),
        }

    def _empty_metrics(self) -> Dict:
        """Return empty metrics structure."""
        return {
            'window_minutes': 0,
            'uptime_seconds': int(time.time() - self._start_time),
            'total_requests': self._total_requests,
            'window_requests': 0,
            'requests_per_minute': 0,
            'response_time': {'avg_ms': 0, 'p50_ms': 0, 'p95_ms': 0, 'p99_ms': 0, 'min_ms': 0, 'max_ms': 0},
            'detection': {'total_items': self._total_items_detected, 'window_items': 0, 'avg_items_per_request': 0},
            'ocr': {'total_boosts': self._total_ocr_boosts, 'window_boosts': 0, 'boost_rate': 0},
            'confidence': {'avg': 0, 'min': 0, 'max': 0, 'above_90': 0, 'above_80': 0, 'above_70': 0, 'below_70': 0},
            'errors': {'total': self._total_errors, 'window': 0, 'rate': 0, 'by_type': {}},
        }

    def reset(self):
        """Reset all metrics (for testing)."""
        self._requests.clear()
        self._total_requests = 0
        self._total_errors = 0
        self._total_items_detected = 0
        self._total_ocr_boosts = 0
        self._start_time = time.time()


# Singleton instance
ai_monitor = AIMonitor()
