from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .auth import build_query_string, create_jwt_token
from .exceptions import UpbitAPIError, UpbitAuthError, UpbitParseError, UpbitRateLimitError
from .types import (
    AccountBalance,
    ApiKeyInfo,
    BatchCancelResult,
    Candle,
    Deposit,
    DepositAddress,
    DepositAddressGeneration,
    DepositAvailability,
    Orderbook,
    OrderbookInstrument,
    Order,
    ParsePolicy,
    ParseStrictLevel,
    RemainingReq,
    ServiceStatus,
    SupportedLevels,
    Ticker,
    TradeTick,
    TradingPair,
    TravelRuleVasp,
    TravelRuleVerification,
    Withdrawal,
    WithdrawalAddress,
    to_upbit_pair,
)


class UpbitClient:
    BASE_URL = "https://api.upbit.com/v1"

    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
        base_url: str = BASE_URL,
        timeout: float = 10.0,
        session: httpx.Client | None = None,
        parse_policy: ParsePolicy | None = None,
    ) -> None:
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or httpx.Client()
        self.parse_policy = parse_policy or ParsePolicy()
        self.last_remaining_req: RemainingReq | None = None

    def list_trading_pairs(self, is_details: bool = False) -> list[TradingPair]:
        raw = self._request("GET", "/market/all", params={"isDetails": str(is_details).lower()})
        return self._parse_list_payload(raw, model_name="TradingPair", parser=TradingPair.from_dict)

    def list_tickers_by_pairs(self, markets: list[str]) -> list[Ticker]:
        raw = self._request("GET", "/ticker", params={"markets": ",".join(to_upbit_pair(m) for m in markets)})
        return self._parse_list_payload(raw, model_name="Ticker", parser=Ticker.from_dict)

    def list_tickers_by_quote_currencies(
        self,
        quote_currencies: list[str],
    ) -> list[Ticker]:
        raw = self._request(
            "GET",
            "/ticker/all",
            params={"quote_currencies": ",".join(quote_currencies)},
        )
        return self._parse_list_payload(raw, model_name="Ticker", parser=Ticker.from_dict)

    def get_orderbook(self, markets: list[str]) -> list[Orderbook]:
        raw = self._request("GET", "/orderbook", params={"markets": ",".join(to_upbit_pair(m) for m in markets)})
        return self._parse_list_payload(raw, model_name="Orderbook", parser=Orderbook.from_dict)

    def list_orderbook_instruments(self, markets: list[str]) -> list[OrderbookInstrument]:
        raw = self._request(
            "GET",
            "/orderbook/instruments",
            params={"markets": ",".join(to_upbit_pair(m) for m in markets)},
        )
        return self._parse_list_payload(
            raw,
            model_name="OrderbookInstrument",
            parser=OrderbookInstrument.from_dict,
        )

    def list_orderbook_supported_levels(self, markets: list[str]) -> list[SupportedLevels]:
        raw = self._request(
            "GET",
            "/orderbook/supported_levels",
            params={"markets": ",".join(to_upbit_pair(m) for m in markets)},
        )
        return self._parse_list_payload(
            raw,
            model_name="SupportedLevels",
            parser=SupportedLevels.from_dict,
        )

    _INTERVAL_MAP: dict[str, tuple[str, int | None]] = {
        "1s": ("/candles/seconds", None),
        "1m": ("/candles/minutes/1", None),
        "3m": ("/candles/minutes/3", None),
        "5m": ("/candles/minutes/5", None),
        "10m": ("/candles/minutes/10", None),
        "15m": ("/candles/minutes/15", None),
        "30m": ("/candles/minutes/30", None),
        "1h": ("/candles/minutes/60", None),
        "4h": ("/candles/minutes/240", None),
        "1d": ("/candles/days", None),
        "1w": ("/candles/weeks", None),
        "1M": ("/candles/months", None),
        "1y": ("/candles/years", None),
    }

    def get_candles(
        self,
        market: str,
        interval: str = "1d",
        count: int | None = None,
        to: str | None = None,
        converting_price_unit: str | None = None,
    ) -> list[Candle]:
        entry = self._INTERVAL_MAP.get(interval)
        if entry is None:
            valid = ", ".join(self._INTERVAL_MAP)
            raise ValueError(f"Unsupported interval: {interval!r}. Valid intervals: {valid}")

        path = entry[0]
        params = self._build_candle_params(market=market, count=count, to=to)
        if converting_price_unit is not None and interval == "1d":
            params["converting_price_unit"] = converting_price_unit
        raw = self._request("GET", path, params=params)
        return self._parse_list_payload(raw, model_name="Candle", parser=Candle.from_dict)

    def recent_trades(self, market: str, count: int | None = None) -> list[TradeTick]:
        params: dict[str, Any] = {"market": to_upbit_pair(market)}
        if count is not None:
            params["count"] = count
        raw = self._request("GET", "/trades/ticks", params=params)
        return self._parse_list_payload(raw, model_name="TradeTick", parser=TradeTick.from_dict)

    def get_balances(self) -> list[AccountBalance]:
        raw = self._request("GET", "/accounts", auth=True)
        return self._parse_list_payload(raw, model_name="AccountBalance", parser=AccountBalance.from_dict)

    def get_open_orders(
        self,
        market: str | None = None,
        states: list[str] | None = None,
        limit: int | None = None,
    ) -> list[Order]:
        params: dict[str, Any] = {}
        if market is not None:
            params["market"] = to_upbit_pair(market)
        if states:
            params["states[]"] = states
        if limit is not None:
            params["limit"] = limit
        raw = self._request("GET", "/orders/open", params=params, auth=True)
        strict, require_trades = self._resolve_order_parse_options(
            self.parse_policy.get_open_orders_level
        )
        return self._parse_list_payload(
            raw,
            model_name="Order",
            parser=lambda item: Order.from_dict(
                item,
                strict=strict,
                require_trades=require_trades,
            ),
        )

    def create_order(
        self,
        market: str,
        side: str,
        ord_type: str,
        volume: str | None = None,
        price: str | None = None,
    ) -> Order:
        body = {
            "market": to_upbit_pair(market),
            "side": side,
            "ord_type": ord_type,
        }
        if volume is not None:
            body["volume"] = volume
        if price is not None:
            body["price"] = price
        raw = self._request("POST", "/orders", json_body=body, auth=True)
        strict, require_trades = self._resolve_order_parse_options(self.parse_policy.create_order_level)
        return self._parse_object_payload(
            raw,
            model_name="Order",
            parser=lambda item: Order.from_dict(
                item,
                strict=strict,
                require_trades=require_trades,
            ),
        )

    def cancel_order(self, uuid: str | None = None, identifier: str | None = None) -> Order:
        if not uuid and not identifier:
            raise ValueError("Either uuid or identifier must be provided.")

        params: dict[str, Any] = {}
        if uuid is not None:
            params["uuid"] = uuid
        if identifier is not None:
            params["identifier"] = identifier

        raw = self._request("DELETE", "/order", params=params, auth=True)
        strict, require_trades = self._resolve_order_parse_options(self.parse_policy.cancel_order_level)
        return self._parse_object_payload(
            raw,
            model_name="Order",
            parser=lambda item: Order.from_dict(
                item,
                strict=strict,
                require_trades=require_trades,
            ),
        )

    def get_order(self, uuid: str | None = None, identifier: str | None = None) -> Order:
        if not uuid and not identifier:
            raise ValueError("Either uuid or identifier must be provided.")

        params: dict[str, Any] = {}
        if uuid is not None:
            params["uuid"] = uuid
        if identifier is not None:
            params["identifier"] = identifier

        raw = self._request("GET", "/order", params=params, auth=True)
        strict, require_trades = self._resolve_order_parse_options(self.parse_policy.get_order_level)
        return self._parse_object_payload(
            raw,
            model_name="Order",
            parser=lambda item: Order.from_dict(
                item,
                strict=strict,
                require_trades=require_trades,
            ),
        )

    def get_available_order_info(self, market: str) -> list[dict[str, Any]]:
        return self._request("GET", "/orders/chance", params={"market": to_upbit_pair(market)}, auth=True)

    def test_create_order(
        self,
        market: str,
        side: str,
        ord_type: str,
        volume: str | None = None,
        price: str | None = None,
        identifier: str | None = None,
        time_in_force: str | None = None,
        smp_type: str | None = None,
    ) -> Order:
        body: dict[str, Any] = {
            "market": to_upbit_pair(market),
            "side": side,
            "ord_type": ord_type,
        }
        if volume is not None:
            body["volume"] = volume
        if price is not None:
            body["price"] = price
        if identifier is not None:
            body["identifier"] = identifier
        if time_in_force is not None:
            body["time_in_force"] = time_in_force
        if smp_type is not None:
            body["smp_type"] = smp_type
        raw = self._request("POST", "/orders/test", json_body=body, auth=True)
        strict, require_trades = self._resolve_order_parse_options(self.parse_policy.create_order_level)
        return self._parse_object_payload(
            raw,
            model_name="Order",
            parser=lambda item: Order.from_dict(
                item,
                strict=strict,
                require_trades=require_trades,
            ),
        )

    def list_orders_by_ids(
        self,
        market: str | None = None,
        uuids: list[str] | None = None,
        identifiers: list[str] | None = None,
        order_by: str | None = None,
    ) -> list[Order]:
        params: dict[str, Any] = {}
        if market is not None:
            params["market"] = to_upbit_pair(market)
        if uuids:
            params["uuids[]"] = uuids
        if identifiers:
            params["identifiers[]"] = identifiers
        if order_by is not None:
            params["order_by"] = order_by
        raw = self._request("GET", "/orders/uuids", params=params, auth=True)
        strict, require_trades = self._resolve_order_parse_options(self.parse_policy.get_open_orders_level)
        return self._parse_list_payload(
            raw,
            model_name="Order",
            parser=lambda item: Order.from_dict(
                item,
                strict=strict,
                require_trades=require_trades,
            ),
        )

    def list_closed_orders(
        self,
        market: str | None = None,
        state: str | None = None,
        states: list[str] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
        order_by: str | None = None,
    ) -> list[Order]:
        params: dict[str, Any] = {}
        if market is not None:
            params["market"] = to_upbit_pair(market)
        if state is not None:
            params["state"] = state
        if states:
            params["states[]"] = states
        if start_time is not None:
            params["start_time"] = start_time
        if end_time is not None:
            params["end_time"] = end_time
        if limit is not None:
            params["limit"] = limit
        if order_by is not None:
            params["order_by"] = order_by
        raw = self._request("GET", "/orders/closed", params=params, auth=True)
        strict, require_trades = self._resolve_order_parse_options(self.parse_policy.get_open_orders_level)
        return self._parse_list_payload(
            raw,
            model_name="Order",
            parser=lambda item: Order.from_dict(
                item,
                strict=strict,
                require_trades=require_trades,
            ),
        )

    def cancel_orders_by_ids(
        self,
        uuids: list[str] | None = None,
        identifiers: list[str] | None = None,
    ) -> BatchCancelResult:
        if not uuids and not identifiers:
            raise ValueError("Either uuids or identifiers must be provided.")

        params: dict[str, Any] = {}
        if uuids:
            params["uuids[]"] = uuids
        if identifiers:
            params["identifiers[]"] = identifiers
        raw = self._request("DELETE", "/orders/uuids", params=params, auth=True)
        return self._parse_object_payload(
            raw,
            model_name="BatchCancelResult",
            parser=BatchCancelResult.from_dict,
        )

    def batch_cancel_orders(
        self,
        quote_currencies: str | None = None,
        cancel_side: str | None = None,
        count: int | None = None,
        order_by: str | None = None,
        pairs: str | None = None,
        exclude_pairs: str | None = None,
    ) -> BatchCancelResult:
        params: dict[str, Any] = {}
        if quote_currencies is not None:
            params["quote_currencies"] = quote_currencies
        if cancel_side is not None:
            params["cancel_side"] = cancel_side
        if count is not None:
            params["count"] = count
        if order_by is not None:
            params["order_by"] = order_by
        if pairs is not None:
            params["pairs"] = ",".join(to_upbit_pair(p) for p in pairs.split(","))
        if exclude_pairs is not None:
            params["exclude_pairs"] = ",".join(to_upbit_pair(p) for p in exclude_pairs.split(","))
        raw = self._request("DELETE", "/orders/open", params=params, auth=True)
        return self._parse_object_payload(
            raw,
            model_name="BatchCancelResult",
            parser=BatchCancelResult.from_dict,
        )

    def cancel_and_new_order(
        self,
        new_ord_type: str,
        prev_order_uuid: str | None = None,
        prev_order_identifier: str | None = None,
        new_volume: str | None = None,
        new_price: str | None = None,
        new_identifier: str | None = None,
        new_time_in_force: str | None = None,
        new_smp_type: str | None = None,
    ) -> dict[str, Any]:
        if not prev_order_uuid and not prev_order_identifier:
            raise ValueError("Either prev_order_uuid or prev_order_identifier must be provided.")

        body: dict[str, Any] = {"new_ord_type": new_ord_type}
        if prev_order_uuid is not None:
            body["prev_order_uuid"] = prev_order_uuid
        if prev_order_identifier is not None:
            body["prev_order_identifier"] = prev_order_identifier
        if new_volume is not None:
            body["new_volume"] = new_volume
        if new_price is not None:
            body["new_price"] = new_price
        if new_identifier is not None:
            body["new_identifier"] = new_identifier
        if new_time_in_force is not None:
            body["new_time_in_force"] = new_time_in_force
        if new_smp_type is not None:
            body["new_smp_type"] = new_smp_type
        return self._request("POST", "/orders/cancel_and_new", json_body=body, auth=True)

    def get_available_withdrawal_info(
        self,
        currency: str,
        net_type: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"currency": currency}
        if net_type is not None:
            params["net_type"] = net_type
        return self._request("GET", "/withdraws/chance", params=params, auth=True)

    def list_withdrawal_addresses(self) -> list[WithdrawalAddress]:
        raw = self._request("GET", "/withdraws/coin_addresses", auth=True)
        return self._parse_list_payload(
            raw,
            model_name="WithdrawalAddress",
            parser=WithdrawalAddress.from_dict,
        )

    def withdraw_coin(
        self,
        currency: str,
        net_type: str,
        amount: str,
        address: str,
        secondary_address: str | None = None,
        transaction_type: str | None = None,
    ) -> Withdrawal:
        body: dict[str, Any] = {
            "currency": currency,
            "net_type": net_type,
            "amount": amount,
            "address": address,
        }
        if secondary_address is not None:
            body["secondary_address"] = secondary_address
        if transaction_type is not None:
            body["transaction_type"] = transaction_type
        raw = self._request("POST", "/withdraws/coin", json_body=body, auth=True)
        return self._parse_object_payload(raw, model_name="Withdrawal", parser=Withdrawal.from_dict)

    def withdraw_krw(self, amount: str, two_factor_type: str) -> Withdrawal:
        body = {
            "amount": amount,
            "two_factor_type": two_factor_type,
        }
        raw = self._request("POST", "/withdraws/krw", json_body=body, auth=True)
        return self._parse_object_payload(raw, model_name="Withdrawal", parser=Withdrawal.from_dict)

    def get_withdrawal(
        self,
        uuid: str | None = None,
        txid: str | None = None,
        currency: str | None = None,
    ) -> Withdrawal:
        params: dict[str, Any] = {}
        if uuid is not None:
            params["uuid"] = uuid
        if txid is not None:
            params["txid"] = txid
        if currency is not None:
            params["currency"] = currency
        raw = self._request("GET", "/withdraw", params=params, auth=True)
        return self._parse_object_payload(raw, model_name="Withdrawal", parser=Withdrawal.from_dict)

    def list_withdrawals(
        self,
        currency: str | None = None,
        state: str | None = None,
        uuids: list[str] | None = None,
        txids: list[str] | None = None,
        limit: int | None = None,
        page: int | None = None,
        order_by: str | None = None,
        from_uuid: str | None = None,
        to_uuid: str | None = None,
    ) -> list[Withdrawal]:
        params: dict[str, Any] = {}
        if currency is not None:
            params["currency"] = currency
        if state is not None:
            params["state"] = state
        if uuids:
            params["uuids[]"] = uuids
        if txids:
            params["txids[]"] = txids
        if limit is not None:
            params["limit"] = limit
        if page is not None:
            params["page"] = page
        if order_by is not None:
            params["order_by"] = order_by
        if from_uuid is not None:
            params["from"] = from_uuid
        if to_uuid is not None:
            params["to"] = to_uuid
        raw = self._request("GET", "/withdraws", params=params, auth=True)
        return self._parse_list_payload(raw, model_name="Withdrawal", parser=Withdrawal.from_dict)

    def cancel_withdrawal(self, uuid: str) -> Withdrawal:
        raw = self._request("DELETE", "/withdraws/coin", params={"uuid": uuid}, auth=True)
        return self._parse_object_payload(raw, model_name="Withdrawal", parser=Withdrawal.from_dict)

    def get_available_deposit_info(self, currency: str, net_type: str) -> DepositAvailability:
        raw = self._request(
            "GET",
            "/deposits/chance/coin",
            params={"currency": currency, "net_type": net_type},
            auth=True,
        )
        return self._parse_object_payload(
            raw,
            model_name="DepositAvailability",
            parser=DepositAvailability.from_dict,
        )

    def create_deposit_address(self, currency: str, net_type: str) -> DepositAddressGeneration:
        raw = self._request(
            "POST",
            "/deposits/generate_coin_address",
            json_body={"currency": currency, "net_type": net_type},
            auth=True,
        )
        return self._parse_object_payload(
            raw,
            model_name="DepositAddressGeneration",
            parser=DepositAddressGeneration.from_dict,
        )

    def get_deposit_address(self, currency: str, net_type: str) -> DepositAddress:
        raw = self._request(
            "GET",
            "/deposits/coin_address",
            params={"currency": currency, "net_type": net_type},
            auth=True,
        )
        return self._parse_object_payload(raw, model_name="DepositAddress", parser=DepositAddress.from_dict)

    def list_deposit_addresses(self) -> list[DepositAddress]:
        raw = self._request("GET", "/deposits/coin_addresses", auth=True)
        return self._parse_list_payload(raw, model_name="DepositAddress", parser=DepositAddress.from_dict)

    def deposit_krw(self, amount: str, two_factor_type: str) -> Deposit:
        raw = self._request(
            "POST",
            "/deposits/krw",
            json_body={"amount": amount, "two_factor_type": two_factor_type},
            auth=True,
        )
        return self._parse_object_payload(raw, model_name="Deposit", parser=Deposit.from_dict)

    def get_deposit(
        self,
        currency: str | None = None,
        uuid: str | None = None,
        txid: str | None = None,
    ) -> Deposit:
        params: dict[str, Any] = {}
        if currency is not None:
            params["currency"] = currency
        if uuid is not None:
            params["uuid"] = uuid
        if txid is not None:
            params["txid"] = txid
        raw = self._request("GET", "/deposit", params=params, auth=True)
        return self._parse_object_payload(raw, model_name="Deposit", parser=Deposit.from_dict)

    def list_deposits(
        self,
        currency: str | None = None,
        state: str | None = None,
        uuids: list[str] | None = None,
        txids: list[str] | None = None,
        limit: int | None = None,
        page: int | None = None,
        order_by: str | None = None,
        from_uuid: str | None = None,
        to_uuid: str | None = None,
    ) -> list[Deposit]:
        params: dict[str, Any] = {}
        if currency is not None:
            params["currency"] = currency
        if state is not None:
            params["state"] = state
        if uuids:
            params["uuids[]"] = uuids
        if txids:
            params["txids[]"] = txids
        if limit is not None:
            params["limit"] = limit
        if page is not None:
            params["page"] = page
        if order_by is not None:
            params["order_by"] = order_by
        if from_uuid is not None:
            params["from"] = from_uuid
        if to_uuid is not None:
            params["to"] = to_uuid
        raw = self._request("GET", "/deposits", params=params, auth=True)
        return self._parse_list_payload(raw, model_name="Deposit", parser=Deposit.from_dict)

    def list_travel_rule_vasps(self) -> list[TravelRuleVasp]:
        raw = self._request("GET", "/travel_rule/vasps", auth=True)
        return self._parse_list_payload(raw, model_name="TravelRuleVasp", parser=TravelRuleVasp.from_dict)

    def verify_travel_rule_by_uuid(self, deposit_uuid: str, vasp_uuid: str) -> TravelRuleVerification:
        raw = self._request(
            "POST",
            "/travel_rule/deposit/uuid",
            json_body={"deposit_uuid": deposit_uuid, "vasp_uuid": vasp_uuid},
            auth=True,
        )
        return self._parse_object_payload(
            raw,
            model_name="TravelRuleVerification",
            parser=TravelRuleVerification.from_dict,
        )

    def verify_travel_rule_by_txid(
        self,
        vasp_uuid: str,
        txid: str,
        currency: str,
        net_type: str,
    ) -> TravelRuleVerification:
        raw = self._request(
            "POST",
            "/travel_rule/deposit/txid",
            json_body={
                "vasp_uuid": vasp_uuid,
                "txid": txid,
                "currency": currency,
                "net_type": net_type,
            },
            auth=True,
        )
        return self._parse_object_payload(
            raw,
            model_name="TravelRuleVerification",
            parser=TravelRuleVerification.from_dict,
        )

    def get_service_status(self) -> list[ServiceStatus]:
        raw = self._request("GET", "/status/wallet", auth=True)
        if not isinstance(raw, list):
            raise UpbitParseError("ServiceStatus", "response", "expected list payload")
        models: list[ServiceStatus] = []
        for item in raw:
            if not isinstance(item, Mapping):
                raise UpbitParseError("ServiceStatus", "response", "list item must be an object")
            models.append(ServiceStatus.from_dict(item))
        return models

    def list_api_keys(self) -> list[ApiKeyInfo]:
        raw = self._request("GET", "/api_keys", auth=True)
        return self._parse_list_payload(raw, model_name="ApiKeyInfo", parser=ApiKeyInfo.from_dict)

    def _build_candle_params(
        self,
        market: str,
        count: int | None,
        to: str | None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"market": to_upbit_pair(market)}
        if count is not None:
            params["count"] = count
        if to is not None:
            params["to"] = to
        return params

    def _parse_list_payload(self, raw: Any, model_name: str, parser: Any) -> list[Any]:
        if not isinstance(raw, list):
            raise UpbitParseError(model_name, "response", "expected list payload")

        models: list[Any] = []
        for item in raw:
            if not isinstance(item, Mapping):
                raise UpbitParseError(model_name, "response", "list item must be an object")
            models.append(parser(item))
        return models

    def _parse_object_payload(self, raw: Any, model_name: str, parser: Any) -> Any:
        if not isinstance(raw, Mapping):
            raise UpbitParseError(model_name, "response", "expected object payload")
        return parser(raw)

    def _resolve_order_parse_options(self, level: ParseStrictLevel) -> tuple[bool, bool]:
        if level is ParseStrictLevel.RELAXED:
            return False, False
        if level is ParseStrictLevel.STRICT:
            return True, False
        if level is ParseStrictLevel.STRICT_WITH_TRADES:
            return True, True
        raise UpbitParseError("ParsePolicy", "level", f"unsupported strict level: {level}")

    def _request(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
        auth: bool = False,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        method_upper = method.upper()

        req_headers: dict[str, str] = {
            "Accept": "application/json",
        }
        if headers:
            req_headers.update(headers)

        query_string = ""
        if method_upper in {"GET", "DELETE"}:
            query_string = build_query_string(params)
        elif method_upper == "POST" and json_body:
            query_string = build_query_string(json_body)
            req_headers.setdefault("Content-Type", "application/json; charset=utf-8")

        if auth:
            if not self.access_key or not self.secret_key:
                raise UpbitAuthError(
                    "This API requires authentication. Provide access_key and secret_key."
                )
            token = create_jwt_token(self.access_key, self.secret_key, query_string)
            req_headers["Authorization"] = f"Bearer {token}"

        response = self.session.request(
            method=method_upper,
            url=url,
            params=params if method_upper in {"GET", "DELETE"} else None,
            json=json_body if method_upper == "POST" else None,
            headers=req_headers,
            timeout=self.timeout,
        )

        self.last_remaining_req = RemainingReq.parse(response.headers.get("Remaining-Req"))

        if not response.is_success:
            self._raise_api_error(response)

        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    def _raise_api_error(self, response: httpx.Response) -> None:
        status_code = response.status_code
        payload: dict[str, Any] | None = None
        name: str | int | None = None
        message = response.text

        try:
            payload = response.json()
            error_obj = payload.get("error", {}) if isinstance(payload, dict) else {}
            name = error_obj.get("name") if isinstance(error_obj, dict) else None
            message = error_obj.get("message", message) if isinstance(error_obj, dict) else message
        except ValueError:
            payload = None

        retry_after: int | None = None
        retry_after_header = response.headers.get("Retry-After")
        if retry_after_header and retry_after_header.isdigit():
            retry_after = int(retry_after_header)

        if status_code in {418, 429}:
            raise UpbitRateLimitError(
                status_code=status_code,
                name=name,
                message=message,
                retry_after=retry_after,
                payload=payload,
            )

        raise UpbitAPIError(
            status_code=status_code,
            name=name,
            message=message,
            payload=payload,
        )
