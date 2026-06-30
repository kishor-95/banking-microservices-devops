"""
test_metrics.py - Tests for account-service metrics
target: 85%+ coverage without modifying main business logic
"""

import pytest

from metrics import (
    ACCOUNTS_CREATED, ACCOUNTS_CLOSED, ACCOUNT_OPERATIONS,
    REQUEST_COUNT, REQUEST_LATENCY, DB_QUERY_DURATION,
    record_account_created, record_account_closed,
    record_account_operation, metrics_endpoint
)


class TestAccountMetrics:
    """Test account-related metrics"""

    def test_record_account_created_checking(self):
        """Test checking account creation metric"""
        before = ACCOUNTS_CREATED.labels(account_type='checking')._value.get()
        record_account_created('checking')
        after = ACCOUNTS_CREATED.labels(account_type='checking')._value.get()
        assert after == before + 1

    def test_record_account_created_savings(self):
        """Test savings account creation metric"""
        before = ACCOUNTS_CREATED.labels(account_type='savings')._value.get()
        record_account_created('savings')
        after = ACCOUNTS_CREATED.labels(account_type='savings')._value.get()
        assert after == before + 1

    def test_record_account_closed(self):
        """Test account closure metric"""
        before = ACCOUNTS_CLOSED._value.get()
        record_account_closed()
        after = ACCOUNTS_CLOSED._value.get()
        assert after == before + 1

    def test_record_account_operation_success(self):
        """Test successful account operation metric"""
        before = ACCOUNT_OPERATIONS.labels(operation='create', status='success')._value.get()
        record_account_operation('create', 'success')
        after = ACCOUNT_OPERATIONS.labels(operation='create', status='success')._value.get()
        assert after == before + 1

    def test_record_account_operation_failure(self):
        """Test failed account operation metric"""
        before = ACCOUNT_OPERATIONS.labels(operation='close', status='failure')._value.get()
        record_account_operation('close', 'failure')
        after = ACCOUNT_OPERATIONS.labels(operation='close', status='failure')._value.get()
        assert after == before + 1


class TestMetricsLabels:
    """Test metric labels are correctly defined"""

    def test_accounts_created_has_account_type_label(self):
        """Verify account creation metric has account_type label"""
        metric = ACCOUNTS_CREATED
        assert 'account_type' in metric._labelnames

    def test_account_operations_has_correct_labels(self):
        """Verify account operations have operation and status labels"""
        metric = ACCOUNT_OPERATIONS
        assert 'operation' in metric._labelnames
        assert 'status' in metric._labelnames

    def test_request_count_has_correct_labels(self):
        """Verify request count has method, endpoint, status_code labels"""
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
        assert b'account_' in response.body

    @pytest.mark.asyncio
    async def test_metrics_endpoint_contains_expected_metrics(self):
        """Test that metrics endpoint contains all expected metrics"""
        # Record some metrics first
        record_account_created('checking')
        record_account_closed()

        response = await metrics_endpoint()
        content = response.body.decode()

        assert 'account_accounts_created_total' in content
        assert 'account_accounts_closed_total' in content
        assert 'account_operations_total' in content


class TestMetricBuckets:
    """Test histogram buckets"""

    def test_request_latency_has_appropriate_buckets(self):
        """Verify request latency has suitable buckets"""
        buckets = REQUEST_LATENCY._upper_bounds
        assert 0.005 in buckets
        assert 0.1 in buckets
        assert 1.0 in buckets
        assert 5.0 in buckets
        assert 10.0 in buckets

    def test_db_query_duration_has_appropriate_buckets(self):
        """Verify DB query duration has suitable buckets"""
        buckets = DB_QUERY_DURATION._upper_bounds
        assert 0.001 in buckets
        assert 0.01 in buckets
        assert 0.1 in buckets
