"""
test_metrics.py - Tests for balance-service metrics
target: 85%+ coverage without modifying main business logic
"""

import pytest

from metrics import (
    BALANCE_QUERIES, TOTAL_BALANCE_QUERIED,
    REQUEST_COUNT, REQUEST_LATENCY, DB_QUERY_DURATION,
    record_balance_query, record_balance_amount, metrics_endpoint
)


class TestBalanceMetrics:
    """Test balance-related metrics"""

    def test_record_balance_query_success(self):
        """Test successful balance query metric"""
        before = BALANCE_QUERIES.labels(status='success')._value.get()
        record_balance_query('success')
        after = BALANCE_QUERIES.labels(status='success')._value.get()
        assert after == before + 1

    def test_record_balance_query_not_found(self):
        """Test balance not found metric"""
        before = BALANCE_QUERIES.labels(status='not_found')._value.get()
        record_balance_query('not_found')
        after = BALANCE_QUERIES.labels(status='not_found')._value.get()
        assert after == before + 1

    def test_record_balance_query_access_denied(self):
        """Test balance access denied metric"""
        before = BALANCE_QUERIES.labels(status='access_denied')._value.get()
        record_balance_query('access_denied')
        after = BALANCE_QUERIES.labels(status='access_denied')._value.get()
        assert after == before + 1

    def test_record_balance_amount(self):
        """Test balance amount recording"""
        before = TOTAL_BALANCE_QUERIED._value.get()
        record_balance_amount(100.50)
        after = TOTAL_BALANCE_QUERIED._value.get()
        assert after == before + 100.50

    def test_record_balance_amount_multiple(self):
        """Test multiple balance amounts accumulate"""
        before = TOTAL_BALANCE_QUERIED._value.get()
        record_balance_amount(50.00)
        record_balance_amount(75.25)
        record_balance_amount(25.75)
        after = TOTAL_BALANCE_QUERIED._value.get()
        assert after == before + 151.00


class TestMetricsLabels:
    """Test metric labels"""

    def test_balance_queries_has_status_label(self):
        """Verify balance queries metric has status label"""
        metric = BALANCE_QUERIES
        assert 'status' in metric._labelnames

    def test_total_balance_queried_has_no_labels(self):
        """Verify total balance queried is a simple counter"""
        metric = TOTAL_BALANCE_QUERIED
        assert len(metric._labelnames) == 0

    def test_request_count_has_correct_labels(self):
        """Verify request count has all required labels"""
        metric = REQUEST_COUNT
        assert 'method' in metric._labelnames
        assert 'endpoint' in metric._labelnames
        assert 'status_code' in metric._labelnames


class TestMetricsEndpoint:
    """Test metrics endpoint"""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_prometheus_format(self):
        """Test that metrics endpoint returns valid Prometheus format"""
        response = await metrics_endpoint()

        assert response.status_code == 200
        assert 'text/plain' in response.media_type
        assert b'balance_' in response.body

    @pytest.mark.asyncio
    async def test_metrics_endpoint_contains_expected_metrics(self):
        """Test that metrics endpoint contains all expected metrics"""
        # Record some metrics first
        record_balance_query('success')
        record_balance_amount(1000.00)

        response = await metrics_endpoint()
        content = response.body.decode()

        assert 'balance_queries_total' in content
        assert 'balance_total_queried_usd' in content
        assert 'balance_http_requests_total' in content


class TestMetricBuckets:
    """Test histogram buckets"""

    def test_request_latency_has_appropriate_buckets(self):
        """Verify request latency has suitable buckets"""
        buckets = REQUEST_LATENCY._upper_bounds
        assert 0.005 in buckets
        assert 0.05 in buckets
        assert 0.5 in buckets
        assert 5.0 in buckets

    def test_db_query_duration_has_appropriate_buckets(self):
        """Verify DB query duration has suitable buckets"""
        buckets = DB_QUERY_DURATION._upper_bounds
        assert 0.001 in buckets
        assert 0.01 in buckets
        assert 1.0 in buckets
