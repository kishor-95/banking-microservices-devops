"""
test_metrics.py - Tests for transaction-service metrics
target: 85%+ coverage without modifying main business logic
"""

import pytest

from metrics import (
    TRANSACTIONS_PROCESSED, TRANSACTION_VOLUME, TRANSACTION_AMOUNT,
    TRANSACTION_ERRORS, REQUEST_LATENCY, DB_QUERY_DURATION,
    record_transaction, record_transaction_error, metrics_endpoint
)


class TestTransactionMetrics:
    """Test transaction-related metrics"""

    def test_record_transaction_deposit_success(self):
        """Test successful deposit metric"""
        before = TRANSACTIONS_PROCESSED.labels(type='DEPOSIT', status='success')._value.get()
        record_transaction('DEPOSIT', 'success', 100.00)
        after = TRANSACTIONS_PROCESSED.labels(type='DEPOSIT', status='success')._value.get()
        assert after == before + 1

    def test_record_transaction_withdraw_failure(self):
        """Test failed withdrawal metric"""
        before = TRANSACTIONS_PROCESSED.labels(type='WITHDRAW', status='failure')._value.get()
        record_transaction('WITHDRAW', 'failure', 50.00)
        after = TRANSACTIONS_PROCESSED.labels(type='WITHDRAW', status='failure')._value.get()
        assert after == before + 1

    def test_record_transaction_insufficient_funds(self):
        """Test insufficient funds transaction metric"""
        before = TRANSACTIONS_PROCESSED.labels(
            type='WITHDRAW', status='insufficient_funds')._value.get()
        record_transaction('WITHDRAW', 'insufficient_funds', 500.00)
        after = TRANSACTIONS_PROCESSED.labels(
            type='WITHDRAW', status='insufficient_funds')._value.get()
        assert after == before + 1

    def test_record_transaction_volume_deposit(self):
        """Test deposit volume tracking"""
        before = TRANSACTION_VOLUME.labels(type='DEPOSIT')._value.get()
        record_transaction('DEPOSIT', 'success', 250.00)
        after = TRANSACTION_VOLUME.labels(type='DEPOSIT')._value.get()
        assert after == before + 250.00

    def test_record_transaction_volume_withdraw(self):
        """Test withdrawal volume tracking"""
        before = TRANSACTION_VOLUME.labels(type='WITHDRAW')._value.get()
        record_transaction('WITHDRAW', 'success', 100.00)
        after = TRANSACTION_VOLUME.labels(type='WITHDRAW')._value.get()
        assert after == before + 100.00

    def test_record_transaction_error_insufficient_funds(self):
        """Test insufficient funds error metric"""
        before = TRANSACTION_ERRORS.labels(error_type='insufficient_funds')._value.get()
        record_transaction_error('insufficient_funds')
        after = TRANSACTION_ERRORS.labels(error_type='insufficient_funds')._value.get()
        assert after == before + 1

    def test_record_transaction_error_account_not_found(self):
        """Test account not found error metric"""
        before = TRANSACTION_ERRORS.labels(error_type='account_not_found')._value.get()
        record_transaction_error('account_not_found')
        after = TRANSACTION_ERRORS.labels(error_type='account_not_found')._value.get()
        assert after == before + 1


class TestMetricsLabels:
    """Test metric labels"""

    def test_transactions_processed_has_correct_labels(self):
        """Verify transactions processed has type and status labels"""
        metric = TRANSACTIONS_PROCESSED
        assert 'type' in metric._labelnames
        assert 'status' in metric._labelnames

    def test_transaction_volume_has_type_label(self):
        """Verify transaction volume has type label"""
        metric = TRANSACTION_VOLUME
        assert 'type' in metric._labelnames

    def test_transaction_amount_has_type_label(self):
        """Verify transaction amount histogram has type label"""
        metric = TRANSACTION_AMOUNT
        assert 'type' in metric._labelnames

    def test_transaction_errors_has_error_type_label(self):
        """Verify transaction errors has error_type label"""
        metric = TRANSACTION_ERRORS
        assert 'error_type' in metric._labelnames


class TestMetricsEndpoint:
    """Test metrics endpoint"""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_prometheus_format(self):
        """Test that metrics endpoint returns valid Prometheus format"""
        response = await metrics_endpoint()

        assert response.status_code == 200
        assert 'text/plain' in response.media_type
        assert b'transaction_' in response.body

    @pytest.mark.asyncio
    async def test_metrics_endpoint_contains_expected_metrics(self):
        """Test that metrics endpoint contains all expected metrics"""
        # Record some metrics first
        record_transaction('DEPOSIT', 'success', 500.00)
        record_transaction_error('insufficient_funds')

        response = await metrics_endpoint()
        content = response.body.decode()

        assert 'transaction_processed_total' in content
        assert 'transaction_volume_usd' in content
        assert 'transaction_errors_total' in content
        assert 'transaction_amount_usd' in content


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

    def test_transaction_amount_has_appropriate_buckets(self):
        """Verify transaction amount has suitable buckets for currency"""
        buckets = TRANSACTION_AMOUNT._upper_bounds
        assert 10 in buckets
        assert 100 in buckets
        assert 1000 in buckets
        assert 10000 in buckets

    def test_db_query_duration_has_appropriate_buckets(self):
        """Verify DB query duration has suitable buckets"""
        buckets = DB_QUERY_DURATION._upper_bounds
        assert 0.001 in buckets
        assert 0.01 in buckets
        assert 1.0 in buckets
