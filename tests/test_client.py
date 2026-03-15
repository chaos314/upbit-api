from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import importlib
from typing import Any

import pytest

from upbit_api import UpbitClient
from upbit_api.exceptions import UpbitAPIError, UpbitAuthError, UpbitParseError, UpbitRateLimitError
from upbit_api.types import (
    AccountBalance,
    ApiKeyInfo,
    BlockState,
    Candle,
    OrderbookInstrument,
    Order,
    OrderSide,
    OrderState,
    OrderType,
    ParsePolicy,
    ParseStrictLevel,
    ServiceStatus,
    SupportedLevels,
    Ticker,
    TradeTick,
    TradingPair,
    WalletState,
)


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        json_data: Any | None = None,
        headers: dict[str, str] | None = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.headers = headers or {}
        self.text = text

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def content(self) -> bytes:
        if self._json_data is None:
            return b""
        return b"x"

    def json(self) -> Any:
        if self._json_data is None:
            raise ValueError("No JSON body")
        return self._json_data


class FakeClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(kwargs)
        return self.response


def _sample_balance() -> dict[str, Any]:
    return {
        "currency": "KRW",
        "balance": "1000000.0",
        "locked": "0.0",
        "avg_buy_price": "0",
        "avg_buy_price_modified": False,
        "unit_currency": "KRW",
    }


def _sample_order() -> dict[str, Any]:
    return {
        "market": "KRW-BTC",
        "uuid": "d098ceaf-6811-4df8-97f2-b7e01aefc03f",
        "side": "bid",
        "ord_type": "limit",
        "price": "140000000",
        "state": "wait",
        "created_at": "2025-07-04T15:00:00+09:00",
        "volume": "1.0",
        "remaining_volume": "1.0",
        "executed_volume": "0.0",
        "executed_funds": "140000000.0",
        "reserved_fee": "70000.0",
        "remaining_fee": "70000.0",
        "paid_fee": "0.0",
        "locked": "140070000.0",
        "prevented_volume": "0",
        "prevented_locked": "0",
        "trades_count": 0,
    }


def _sample_trade() -> dict[str, Any]:
    return {
        "market": "KRW-BTC",
        "uuid": "795dff29-bba6-49b2-baab-63473ab7931c",
        "price": "140000000",
        "volume": "0.1",
        "funds": "14000000",
        "trend": "up",
        "created_at": "2025-07-04T15:00:01.123+09:00",
        "side": "bid",
    }


def _sample_order_with_trades() -> dict[str, Any]:
    order = _sample_order()
    order["trades"] = [_sample_trade()]
    return order


def _sample_batch_cancel_result() -> dict[str, Any]:
    return {
        "success": {
            "count": 1,
            "orders": [{"uuid": "u1", "market": "KRW-BTC"}],
        },
        "failed": {
            "count": 0,
            "orders": [],
        },
    }


def _sample_withdrawal() -> dict[str, Any]:
    return {
        "type": "withdraw",
        "uuid": "w1",
        "currency": "BTC",
        "txid": None,
        "state": "WAITING",
        "created_at": "2025-07-04T15:00:00+09:00",
        "done_at": None,
        "amount": "0.01",
        "fee": "0.0005",
        "transaction_type": "default",
        "is_cancelable": True,
        "net_type": "BTC",
    }


def _sample_deposit_availability() -> dict[str, Any]:
    return {
        "currency": "BTC",
        "net_type": "BTC",
        "is_deposit_possible": True,
        "deposit_impossible_reason": "",
        "minimum_deposit_amount": "0.0001",
        "minimum_deposit_confirmations": 1,
        "decimal_precision": 8,
    }


def _sample_deposit_address() -> dict[str, Any]:
    return {
        "currency": "BTC",
        "net_type": "BTC",
        "deposit_address": "addr",
        "secondary_address": None,
    }


def _sample_deposit() -> dict[str, Any]:
    return {
        "type": "deposit",
        "uuid": "d1",
        "currency": "BTC",
        "txid": None,
        "state": "PROCESSING",
        "created_at": "2025-07-04T15:00:00+09:00",
        "done_at": None,
        "amount": "0.01",
        "fee": "0",
        "transaction_type": "default",
        "net_type": "BTC",
    }


def _sample_travel_rule_vasp() -> dict[str, Any]:
    return {
        "vasp_name": "Example VASP",
        "vasp_uuid": "v1",
        "depositable": True,
        "withdrawable": True,
    }


def _sample_travel_rule_verification() -> dict[str, Any]:
    return {
        "deposit_uuid": "d1",
        "verification_result": "OK",
        "deposit_state": "ACCEPTED",
    }


def _sample_ticker() -> dict[str, Any]:
    return {
        "market": "KRW-BTC",
        "trade_price": "140000000",
        "signed_change_rate": "0.0123",
        "acc_trade_price_24h": "123456789.12",
        "acc_trade_volume_24h": "12.3456",
        "timestamp": 1710000000000,
    }


def _sample_trade_tick() -> dict[str, Any]:
    return {
        "market": "KRW-BTC",
        "trade_date_utc": "2026-03-15",
        "trade_time_utc": "00:00:00",
        "timestamp": 1710000000000,
        "trade_price": "140000000",
        "trade_volume": "0.001",
        "ask_bid": "bid",
    }


def test_package_root_exports_typed_exchange_models() -> None:
    pkg = importlib.import_module("upbit_api")

    assert hasattr(pkg, "TradingPair")
    assert hasattr(pkg, "Ticker")
    assert hasattr(pkg, "Candle")
    assert hasattr(pkg, "Withdrawal")
    assert hasattr(pkg, "Deposit")
    assert hasattr(pkg, "TravelRuleVerification")
    assert hasattr(pkg, "BatchCancelResult")


def test_public_request_parses_remaining_req() -> None:
    response = FakeResponse(
        status_code=200,
        json_data=[{"market": "KRW-BTC"}],
        headers={"Remaining-Req": "group=market; min=1800; sec=8"},
    )
    session = FakeClient(response)
    client = UpbitClient(session=session)

    data = client.list_trading_pairs()

    assert isinstance(data[0], TradingPair)
    assert data[0].market == "KRW-BTC"
    assert client.last_remaining_req is not None
    assert client.last_remaining_req.group == "market"
    assert client.last_remaining_req.sec == 8


def test_private_request_sets_bearer_token() -> None:
    response = FakeResponse(status_code=200, json_data=[_sample_balance()])
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    client.get_balances()

    headers = session.calls[0]["headers"]
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Bearer ")


def test_private_request_requires_keys() -> None:
    response = FakeResponse(status_code=200, json_data=[_sample_balance()])
    session = FakeClient(response)
    client = UpbitClient(session=session)

    with pytest.raises(UpbitAuthError):
        client.get_balances()


def test_raises_rate_limit_error_with_retry_after() -> None:
    response = FakeResponse(
        status_code=429,
        json_data={"error": {"name": "too_many_requests", "message": "rate exceeded"}},
        headers={"Retry-After": "2"},
        text="rate exceeded",
    )
    session = FakeClient(response)
    client = UpbitClient(session=session)

    with pytest.raises(UpbitRateLimitError) as exc:
        client.list_tickers_by_pairs(["KRW-BTC"])

    assert exc.value.status_code == 429
    assert exc.value.retry_after == 2


def test_raises_api_error_for_non_rate_limit() -> None:
    response = FakeResponse(
        status_code=401,
        json_data={"error": {"name": "jwt_verification", "message": "invalid jwt"}},
        text="invalid jwt",
    )
    session = FakeClient(response)
    client = UpbitClient(session=session)

    with pytest.raises(UpbitAPIError) as exc:
        client.list_tickers_by_pairs(["KRW-BTC"])

    assert exc.value.status_code == 401
    assert exc.value.name == "jwt_verification"


def test_list_tickers_by_quote_currencies_calls_expected_endpoint() -> None:
    response = FakeResponse(status_code=200, json_data=[{"market": "KRW-BTC"}])
    session = FakeClient(response)
    client = UpbitClient(session=session)

    data = client.list_tickers_by_quote_currencies(["KRW", "BTC"])

    assert isinstance(data[0], Ticker)
    assert data[0].market == "KRW-BTC"
    assert session.calls[0]["url"].endswith("/ticker/all")
    assert session.calls[0]["params"] == {"quote_currencies": "KRW,BTC"}


def test_list_orderbook_instruments_calls_expected_endpoint() -> None:
    response = FakeResponse(
        status_code=200,
        json_data=[
            {
                "market": "KRW-BTC",
                "quote_currency": "KRW",
                "tick_size": "1000",
                "supported_levels": ["0", "10000"],
            }
        ],
    )
    session = FakeClient(response)
    client = UpbitClient(session=session)

    data = client.list_orderbook_instruments(["KRW-BTC", "KRW-ETH"])

    assert isinstance(data[0], OrderbookInstrument)
    assert data[0].quote_currency == "KRW"
    assert session.calls[0]["url"].endswith("/orderbook/instruments")
    assert session.calls[0]["params"] == {"markets": "KRW-BTC,KRW-ETH"}


def test_list_orderbook_supported_levels_calls_expected_endpoint() -> None:
    response = FakeResponse(
        status_code=200,
        json_data=[{"market": "KRW-BTC", "supported_levels": [0, 10000]}],
    )
    session = FakeClient(response)
    client = UpbitClient(session=session)

    data = client.list_orderbook_supported_levels(["KRW-BTC", "KRW-ETH"])

    assert isinstance(data[0], SupportedLevels)
    assert data[0].market == "KRW-BTC"
    assert session.calls[0]["url"].endswith("/orderbook/supported_levels")
    assert session.calls[0]["params"] == {"markets": "KRW-BTC,KRW-ETH"}


@pytest.mark.parametrize(
    ("method_name", "path"),
    [
        ("list_second_candles", "/candles/seconds"),
        ("list_day_candles", "/candles/days"),
        ("list_week_candles", "/candles/weeks"),
        ("list_month_candles", "/candles/months"),
        ("list_year_candles", "/candles/years"),
    ],
)
def test_candle_endpoints_call_expected_path(method_name: str, path: str) -> None:
    response = FakeResponse(status_code=200, json_data=[{"market": "KRW-BTC"}])
    session = FakeClient(response)
    client = UpbitClient(session=session)

    method = getattr(client, method_name)
    if method_name == "list_day_candles":
        data = method(
            "KRW-BTC",
            count=3,
            to="2026-03-15T00:00:00Z",
            converting_price_unit="KRW",
        )
        assert session.calls[0]["params"] == {
            "market": "KRW-BTC",
            "count": 3,
            "to": "2026-03-15T00:00:00Z",
            "converting_price_unit": "KRW",
        }
    else:
        data = method("KRW-BTC", count=3, to="2026-03-15T00:00:00Z")
        assert session.calls[0]["params"] == {
            "market": "KRW-BTC",
            "count": 3,
            "to": "2026-03-15T00:00:00Z",
        }

    assert isinstance(data[0], Candle)
    assert data[0].market == "KRW-BTC"
    assert session.calls[0]["url"].endswith(path)


def test_ticker_parses_mixed_numeric_value_types() -> None:
    payload = _sample_ticker()
    payload["trade_price"] = 140000000
    payload["signed_change_rate"] = 0.0123
    payload["acc_trade_price_24h"] = "123456789.12"
    payload["acc_trade_volume_24h"] = 12.3456

    response = FakeResponse(status_code=200, json_data=[payload])
    session = FakeClient(response)
    client = UpbitClient(session=session)

    data = client.list_tickers_by_pairs(["KRW-BTC"])

    assert isinstance(data[0], Ticker)
    assert data[0].trade_price == Decimal("140000000")
    assert data[0].signed_change_rate == Decimal("0.0123")
    assert data[0].acc_trade_price_24h == Decimal("123456789.12")
    assert data[0].acc_trade_volume_24h == Decimal("12.3456")


def test_ticker_raises_parse_error_on_invalid_numeric_type() -> None:
    payload = _sample_ticker()
    payload["trade_price"] = {"unexpected": "object"}

    response = FakeResponse(status_code=200, json_data=[payload])
    session = FakeClient(response)
    client = UpbitClient(session=session)

    with pytest.raises(UpbitParseError):
        client.list_tickers_by_pairs(["KRW-BTC"])


def test_candle_allows_optional_null_fields() -> None:
    payload = {
        "market": "KRW-BTC",
        "candle_date_time_utc": None,
        "candle_date_time_kst": None,
        "opening_price": None,
        "high_price": None,
        "low_price": None,
        "trade_price": None,
        "timestamp": None,
        "candle_acc_trade_price": None,
        "candle_acc_trade_volume": None,
        "unit": None,
    }
    response = FakeResponse(status_code=200, json_data=[payload])
    session = FakeClient(response)
    client = UpbitClient(session=session)

    data = client.list_second_candles("KRW-BTC")

    assert isinstance(data[0], Candle)
    assert data[0].market == "KRW-BTC"
    assert data[0].trade_price is None


def test_recent_trades_raises_parse_error_on_invalid_ask_bid() -> None:
    payload = _sample_trade_tick()
    payload["ask_bid"] = "invalid-side"

    response = FakeResponse(status_code=200, json_data=[payload])
    session = FakeClient(response)
    client = UpbitClient(session=session)

    with pytest.raises(UpbitParseError):
        client.recent_trades("KRW-BTC")


def test_recent_trades_allows_missing_ask_bid() -> None:
    payload = _sample_trade_tick()
    payload["ask_bid"] = None

    response = FakeResponse(status_code=200, json_data=[payload])
    session = FakeClient(response)
    client = UpbitClient(session=session)

    data = client.recent_trades("KRW-BTC")

    assert isinstance(data[0], TradeTick)
    assert data[0].ask_bid is None


def test_withdrawal_raises_parse_error_on_unknown_state() -> None:
    payload = _sample_withdrawal()
    payload["state"] = "UNKNOWN"

    response = FakeResponse(status_code=200, json_data=payload)
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    with pytest.raises(UpbitParseError):
        client.get_withdrawal(uuid="w1")


def test_withdrawal_raises_parse_error_on_unknown_transaction_type() -> None:
    payload = _sample_withdrawal()
    payload["transaction_type"] = "unsupported"

    response = FakeResponse(status_code=200, json_data=payload)
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    with pytest.raises(UpbitParseError):
        client.get_withdrawal(uuid="w1")


def test_deposit_raises_parse_error_on_unknown_state() -> None:
    payload = _sample_deposit()
    payload["state"] = "UNKNOWN"

    response = FakeResponse(status_code=200, json_data=payload)
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    with pytest.raises(UpbitParseError):
        client.get_deposit(uuid="d1")


def test_deposit_raises_parse_error_on_unknown_transaction_type() -> None:
    payload = _sample_deposit()
    payload["transaction_type"] = "unsupported"

    response = FakeResponse(status_code=200, json_data=payload)
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    with pytest.raises(UpbitParseError):
        client.get_deposit(uuid="d1")


def test_travel_rule_verification_raises_parse_error_on_unknown_deposit_state() -> None:
    payload = _sample_travel_rule_verification()
    payload["deposit_state"] = "UNKNOWN"

    response = FakeResponse(status_code=200, json_data=payload)
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    with pytest.raises(UpbitParseError):
        client.verify_travel_rule_by_uuid(deposit_uuid="d1", vasp_uuid="v1")


def test_cancel_order_requires_uuid_or_identifier() -> None:
    response = FakeResponse(status_code=200, json_data=_sample_order())
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    with pytest.raises(ValueError):
        client.cancel_order()


def test_get_service_status_calls_expected_endpoint() -> None:
    response = FakeResponse(
        status_code=200,
        json_data=[
            {
                "currency": "BTC",
                "wallet_state": "working",
                "block_state": "normal",
                "block_height": 903942,
                "block_updated_at": "2025-07-04T08:02:05.526+00:00",
                "block_elapsed_minutes": 6,
                "net_type": "BTC",
                "network_name": "Bitcoin",
            }
        ],
    )
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    data = client.get_service_status()

    assert isinstance(data[0], ServiceStatus)
    assert data[0].currency == "BTC"
    assert data[0].wallet_state is WalletState.WORKING
    assert data[0].block_state is BlockState.NORMAL
    assert data[0].block_updated_at == datetime.fromisoformat("2025-07-04T08:02:05.526+00:00")
    assert data[0].block_elapsed_minutes == 6
    assert session.calls[0]["url"].endswith("/status/wallet")


def test_list_api_keys_calls_expected_endpoint() -> None:
    response = FakeResponse(
        status_code=200,
        json_data=[{"access_key": "test-access-key", "expire_at": "2026-07-01T09:00:00+09:00"}],
    )
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    data = client.list_api_keys()

    assert isinstance(data[0], ApiKeyInfo)
    assert data[0].access_key == "test-access-key"
    assert data[0].expire_at == datetime.fromisoformat("2026-07-01T09:00:00+09:00")
    assert session.calls[0]["url"].endswith("/api_keys")


def test_service_status_raises_parse_error_on_unknown_wallet_state() -> None:
    response = FakeResponse(
        status_code=200,
        json_data=[
            {
                "currency": "BTC",
                "wallet_state": "unknown-state",
                "net_type": "BTC",
                "network_name": "Bitcoin",
            }
        ],
    )
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    with pytest.raises(UpbitParseError):
        client.get_service_status()


def test_api_keys_raises_parse_error_on_missing_expire_at() -> None:
    response = FakeResponse(status_code=200, json_data=[{"access_key": "test-access-key"}])
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    with pytest.raises(UpbitParseError):
        client.list_api_keys()


def test_get_balances_parses_typed_model() -> None:
    response = FakeResponse(status_code=200, json_data=[_sample_balance()])
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    balances = client.get_balances()

    assert isinstance(balances[0], AccountBalance)
    assert balances[0].currency == "KRW"
    assert balances[0].balance == Decimal("1000000.0")


def test_get_order_parses_typed_model() -> None:
    response = FakeResponse(status_code=200, json_data=_sample_order_with_trades())
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    order = client.get_order(uuid="d098ceaf-6811-4df8-97f2-b7e01aefc03f")

    assert isinstance(order, Order)
    assert order.side is OrderSide.BID
    assert order.ord_type is OrderType.LIMIT
    assert order.state is OrderState.WAIT
    assert order.price == Decimal("140000000")
    assert order.created_at == datetime.fromisoformat("2025-07-04T15:00:00+09:00")
    assert order.trades is not None
    assert len(order.trades) == 1


def test_get_open_orders_parses_typed_models() -> None:
    response = FakeResponse(status_code=200, json_data=[_sample_order()])
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    orders = client.get_open_orders(states=["wait"])

    assert len(orders) == 1
    assert isinstance(orders[0], Order)
    assert orders[0].uuid == "d098ceaf-6811-4df8-97f2-b7e01aefc03f"


def test_order_parse_error_on_unknown_state() -> None:
    payload = _sample_order_with_trades()
    payload["state"] = "unknown-state"
    response = FakeResponse(status_code=200, json_data=payload)
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    with pytest.raises(UpbitParseError):
        client.get_order(uuid="d098ceaf-6811-4df8-97f2-b7e01aefc03f")


def test_get_order_strict_requires_trades_by_default() -> None:
    response = FakeResponse(status_code=200, json_data=_sample_order())
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    with pytest.raises(UpbitParseError):
        client.get_order(uuid="d098ceaf-6811-4df8-97f2-b7e01aefc03f")


def test_get_order_relaxed_allows_missing_trades() -> None:
    response = FakeResponse(status_code=200, json_data=_sample_order())
    session = FakeClient(response)
    policy = ParsePolicy(get_order_level=ParseStrictLevel.RELAXED)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
        parse_policy=policy,
    )

    order = client.get_order(uuid="d098ceaf-6811-4df8-97f2-b7e01aefc03f")

    assert isinstance(order, Order)
    assert order.trades is None


def test_order_extended_endpoints_call_expected_paths() -> None:
    response = FakeResponse(status_code=200, json_data=_sample_order())
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    client.get_available_order_info("KRW-BTC")
    assert session.calls[-1]["url"].endswith("/orders/chance")
    assert session.calls[-1]["params"] == {"market": "KRW-BTC"}

    client.test_create_order(
        market="KRW-BTC",
        side="bid",
        ord_type="limit",
        volume="0.001",
        price="50000000",
        time_in_force="ioc",
    )
    assert session.calls[-1]["url"].endswith("/orders/test")
    assert session.calls[-1]["json"]["market"] == "KRW-BTC"

    response._json_data = []
    client.list_orders_by_ids(market="KRW-BTC", uuids=["u1", "u2"], order_by="desc")
    assert session.calls[-1]["url"].endswith("/orders/uuids")
    assert session.calls[-1]["params"]["uuids[]"] == ["u1", "u2"]

    client.list_closed_orders(market="KRW-BTC", states=["done", "cancel"], limit=50)
    assert session.calls[-1]["url"].endswith("/orders/closed")
    assert session.calls[-1]["params"]["states[]"] == ["done", "cancel"]

    response._json_data = _sample_batch_cancel_result()
    client.cancel_orders_by_ids(uuids=["u1"])
    assert session.calls[-1]["url"].endswith("/orders/uuids")
    assert session.calls[-1]["method"] == "DELETE"

    client.batch_cancel_orders(cancel_side="all", count=10, pairs="KRW-BTC,KRW-ETH")
    assert session.calls[-1]["url"].endswith("/orders/open")
    assert session.calls[-1]["method"] == "DELETE"

    client.cancel_and_new_order(
        prev_order_uuid="u1",
        new_ord_type="limit",
        new_price="100000000",
        new_volume="1",
    )
    assert session.calls[-1]["url"].endswith("/orders/cancel_and_new")
    assert session.calls[-1]["json"]["new_ord_type"] == "limit"


def test_withdraw_endpoints_call_expected_paths() -> None:
    response = FakeResponse(status_code=200, json_data={"ok": True})
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    client.get_available_withdrawal_info("BTC", net_type="BTC")
    assert session.calls[-1]["url"].endswith("/withdraws/chance")

    response._json_data = []
    client.list_withdrawal_addresses()
    assert session.calls[-1]["url"].endswith("/withdraws/coin_addresses")

    response._json_data = _sample_withdrawal()
    client.withdraw_coin(
        currency="BTC",
        net_type="BTC",
        amount="0.01",
        address="addr",
        transaction_type="default",
    )
    assert session.calls[-1]["url"].endswith("/withdraws/coin")
    assert session.calls[-1]["json"]["net_type"] == "BTC"

    client.withdraw_krw(amount="10000", two_factor_type="naver")
    assert session.calls[-1]["url"].endswith("/withdraws/krw")

    client.get_withdrawal(currency="BTC")
    assert session.calls[-1]["url"].endswith("/withdraw")

    response._json_data = [_sample_withdrawal()]
    client.list_withdrawals(currency="BTC", uuids=["w1"], limit=10)
    assert session.calls[-1]["url"].endswith("/withdraws")
    assert session.calls[-1]["params"]["uuids[]"] == ["w1"]

    canceled = _sample_withdrawal()
    canceled["state"] = "CANCELLED"
    canceled["is_cancelable"] = False
    response._json_data = canceled
    client.cancel_withdrawal("w1")
    assert session.calls[-1]["url"].endswith("/withdraws/coin")
    assert session.calls[-1]["method"] == "DELETE"


def test_deposit_and_travel_rule_endpoints_call_expected_paths() -> None:
    response = FakeResponse(status_code=200, json_data=_sample_deposit_availability())
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    client.get_available_deposit_info(currency="BTC", net_type="BTC")
    assert session.calls[-1]["url"].endswith("/deposits/chance/coin")

    response._json_data = _sample_deposit_address()
    client.create_deposit_address(currency="BTC", net_type="BTC")
    assert session.calls[-1]["url"].endswith("/deposits/generate_coin_address")

    response._json_data = _sample_deposit_address()
    client.get_deposit_address(currency="BTC", net_type="BTC")
    assert session.calls[-1]["url"].endswith("/deposits/coin_address")

    response._json_data = []
    client.list_deposit_addresses()
    assert session.calls[-1]["url"].endswith("/deposits/coin_addresses")

    response._json_data = _sample_deposit()
    client.deposit_krw(amount="10000", two_factor_type="kakao")
    assert session.calls[-1]["url"].endswith("/deposits/krw")

    client.get_deposit(currency="BTC")
    assert session.calls[-1]["url"].endswith("/deposit")

    response._json_data = [_sample_deposit()]
    client.list_deposits(currency="BTC", txids=["t1"], page=2)
    assert session.calls[-1]["url"].endswith("/deposits")
    assert session.calls[-1]["params"]["txids[]"] == ["t1"]

    response._json_data = [_sample_travel_rule_vasp()]
    client.list_travel_rule_vasps()
    assert session.calls[-1]["url"].endswith("/travel_rule/vasps")

    response._json_data = _sample_travel_rule_verification()
    client.verify_travel_rule_by_uuid(deposit_uuid="d1", vasp_uuid="v1")
    assert session.calls[-1]["url"].endswith("/travel_rule/deposit/uuid")

    client.verify_travel_rule_by_txid(
        vasp_uuid="v1",
        txid="t1",
        currency="BTC",
        net_type="BTC",
    )
    assert session.calls[-1]["url"].endswith("/travel_rule/deposit/txid")


def test_new_validations_raise_value_error() -> None:
    response = FakeResponse(status_code=200, json_data={"ok": True})
    session = FakeClient(response)
    client = UpbitClient(
        access_key="test-access-key",
        secret_key="s" * 64,
        session=session,
    )

    with pytest.raises(ValueError):
        client.cancel_orders_by_ids()

    with pytest.raises(ValueError):
        client.cancel_and_new_order(new_ord_type="limit")
