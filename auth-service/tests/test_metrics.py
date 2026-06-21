"""
test_metrics.py - Tests for auth-service metrics
target: 85%+ coverage without modifying main business logic
"""

import pytest

from metrics import (
    REQUEST_COUNT, REQUEST_LATENCY, REQUESTS_IN_PROGRESS,
    LOGIN_ATTEMPTS, REGISTRATIONS, TOKEN_OPERATIONS,
    DB_CONNECTION_ERRORS, DB_QUERY_DURATION,
    record_login, record_registration, record_token_operation,
    metrics_endpoint
)


class TestMetricsCounters:
    """Test metric counter increments"""

    def test_record_login_success(self):
        """Test login success metric recording"""
        before = LOGIN_ATTEMPTS.labels(status='success')._value.get()
        record_login('success')
        after = LOGIN_ATTEMPTS.labels(status='success')._value.get()
        assert after == before + 1

    def test_record_login_failure(self):
        """Test login failure metric recording"""
        before = LOGIN_ATTEMPTS.labels(status='failure')._value.get()
        record_login('failure')
        after = LOGIN_ATTEMPTS.labels(status='failure')._value.get()
        assert after == before + 1

    def test_record_registration_success(self):
        """Test registration success metric recording"""
        before = REGISTRATIONS.labels(status='success')._value.get()
        record_registration('success')
        after = REGISTRATIONS.labels(status='success')._value.get()
        assert after == before + 1

    def test_record_registration_duplicate(self):
        """Test registration duplicate metric recording"""
        before = REGISTRATIONS.labels(status='duplicate')._value.get()
        record_registration('duplicate')
        after = REGISTRATIONS.labels(status='duplicate')._value.get()
        assert after == before + 1

    def test_record_token_create_success(self):
        """Test token creation success metric"""
        before = TOKEN_OPERATIONS.labels(operation='create', status='success')._value.get()
        record_token_operation('create', 'success')
        after = TOKEN_OPERATIONS.labels(operation='create', status='success')._value.get()
        assert after == before + 1

    def test_record_token_verify_failure(self):
        """Test token verification failure metric"""
        before = TOKEN_OPERATIONS.labels(operation='verify', status='failure')._value.get()
        record_token_operation('verify', 'failure')
        after = TOKEN_OPERATIONS.labels(operation='verify', status='failure')._value.get()
        assert after == before + 1


class TestDatabaseMetrics:
    """Test database query metrics"""

    def test_db_connection_errors_increment(self):
        """Test DB connection error counter can be incremented"""
        before = DB_CONNECTION_ERRORS._value.get()
        DB_CONNECTION_ERRORS.inc()
        after = DB_CONNECTION_ERRORS._value.get()
        assert after == before + 1

    def test_db_query_duration_buckets(self):
        """Test DB query duration histogram buckets exist"""
        buckets = DB_QUERY_DURATION._upper_bounds
        assert 0.001 in buckets
        assert 0.01 in buckets
        assert 1.0 in buckets


class TestMetricsEndpoint:
    """Test metrics endpoint"""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_prometheus_format(self):
        """Test that metrics endpoint returns valid Prometheus format"""
        response = await metrics_endpoint()

        assert response.status_code == 200
        assert 'text/plain' in response.media_type
        assert b'auth_' in response.body  # Contains auth metrics

    @pytest.mark.asyncio
    async def test_metrics_endpoint_contains_expected_metrics(self):
        """Test that metrics endpoint contains all expected metrics"""
        # Record some metrics first
        record_login('success')
        record_registration('success')

        response = await metrics_endpoint()
        content = response.body.decode()

        assert 'auth_login_attempts_total' in content
        assert 'auth_registrations_total' in content
        assert 'auth_http_requests_total' in content
        assert 'auth_http_request_duration_seconds' in content


class TestMetricsExistence:
    """Test that all expected metrics are defined"""

    def test_all_counters_are_defined(self):
        """Test all expected metrics exist"""
        assert LOGIN_ATTEMPTS is not None
        assert REGISTRATIONS is not None
        assert TOKEN_OPERATIONS is not None
        assert DB_CONNECTION_ERRORS is not None
        assert REQUEST_COUNT is not None

    def test_all_histograms_are_defined(self):
        """Test all expected histograms exist"""
        assert REQUEST_LATENCY is not None
        assert DB_QUERY_DURATION is not None

    def test_gauges_are_defined(self):
        """Test all expected gauges exist"""
        assert REQUESTS_IN_PROGRESS is not None


class TestMetricLabels:
    """Test metric labels are correctly applied"""

    def test_login_metrics_have_correct_labels(self):
        """Verify login metrics have status label"""
        metric = LOGIN_ATTEMPTS
        assert 'status' in metric._labelnames

    def test_registration_metrics_have_correct_labels(self):
        """Verify registration metrics have status label"""
        metric = REGISTRATIONS
        assert 'status' in metric._labelnames

    def test_token_operations_have_correct_labels(self):
        """Verify token operations have operation and status labels"""
        metric = TOKEN_OPERATIONS
        assert 'operation' in metric._labelnames
        assert 'status' in metric._labelnames

    def test_request_count_has_correct_labels(self):
        """Verify request count has method, endpoint, status_code labels"""
        metric = REQUEST_COUNT
        assert 'method' in metric._labelnames
        assert 'endpoint' in metric._labelnames
        assert 'status_code' in metric._labelnames


class TestMetricBuckets:
    """Test histogram buckets are appropriately defined"""

    def test_request_latency_has_appropriate_buckets(self):
        """Verify request latency has suitable buckets for HTTP requests"""
        buckets = REQUEST_LATENCY._upper_bounds
        # Should have buckets from 5ms to 10s
        assert 0.005 in buckets
        assert 0.01 in buckets
        assert 0.1 in buckets
        assert 1.0 in buckets
        assert 5.0 in buckets
        assert 10.0 in buckets

    def test_db_query_duration_has_appropriate_buckets(self):
        """Verify DB query duration has suitable buckets for DB operations"""
        buckets = DB_QUERY_DURATION._upper_bounds
        # Should have buckets from 1ms to 1s
        assert 0.001 in buckets
        assert 0.01 in buckets
        assert 0.1 in buckets
        assert 1.0 in buckets
