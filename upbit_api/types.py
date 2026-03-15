from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping

from .exceptions import UpbitParseError


@dataclass(slots=True)
class RemainingReq:
    group: str | None = None
    sec: int | None = None
    min: int | None = None

    @classmethod
    def parse(cls, value: str | None) -> "RemainingReq | None":
        if not value:
            return None

        items = {}
        for part in value.split(";"):
            token = part.strip()
            if "=" not in token:
                continue
            key, raw = token.split("=", 1)
            items[key.strip()] = raw.strip()

        sec = _safe_int(items.get("sec"))
        min_value = _safe_int(items.get("min"))
        return cls(group=items.get("group"), sec=sec, min=min_value)


@dataclass(slots=True)
class ServiceStatus:
    currency: str
    wallet_state: "WalletState"
    block_state: "BlockState | None" = None
    block_height: int | None = None
    block_updated_at: datetime | None = None
    block_elapsed_minutes: int | None = None
    net_type: str | None = None
    network_name: str | None = None

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "ServiceStatus":
        wallet_state = _parse_wallet_state(item.get("wallet_state"))
        block_state = _parse_block_state(item.get("block_state"))
        block_updated_at = _parse_datetime(item.get("block_updated_at"))

        return cls(
            currency=_require_str(item, "currency", "ServiceStatus"),
            wallet_state=wallet_state,
            block_state=block_state,
            block_height=_safe_int_from_any(item.get("block_height")),
            block_updated_at=block_updated_at,
            block_elapsed_minutes=_safe_int_from_any(item.get("block_elapsed_minutes")),
            net_type=_require_str(item, "net_type", "ServiceStatus"),
            network_name=_require_str(item, "network_name", "ServiceStatus"),
        )


@dataclass(slots=True)
class ApiKeyInfo:
    access_key: str
    expire_at: datetime

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "ApiKeyInfo":
        expire_at_raw = _require_str(item, "expire_at", "ApiKeyInfo")
        return cls(
            access_key=_require_str(item, "access_key", "ApiKeyInfo"),
            expire_at=_parse_datetime(expire_at_raw, model="ApiKeyInfo", field="expire_at"),
        )


@dataclass(slots=True)
class AccountBalance:
    currency: str
    balance: Decimal
    locked: Decimal
    avg_buy_price: Decimal
    avg_buy_price_modified: bool
    unit_currency: str

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "AccountBalance":
        return cls(
            currency=_require_str(item, "currency", "AccountBalance"),
            balance=_parse_decimal(item.get("balance"), "AccountBalance", "balance", required=True),
            locked=_parse_decimal(item.get("locked"), "AccountBalance", "locked", required=True),
            avg_buy_price=_parse_decimal(
                item.get("avg_buy_price"),
                "AccountBalance",
                "avg_buy_price",
                required=True,
            ),
            avg_buy_price_modified=_require_bool(
                item,
                "avg_buy_price_modified",
                "AccountBalance",
            ),
            unit_currency=_require_str(item, "unit_currency", "AccountBalance"),
        )


@dataclass(slots=True)
class TradingPair:
    market: str
    korean_name: str | None = None
    english_name: str | None = None
    market_event: Mapping[str, Any] | None = None

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "TradingPair":
        return cls(
            market=_require_str(item, "market", "TradingPair"),
            korean_name=_as_str(item.get("korean_name")),
            english_name=_as_str(item.get("english_name")),
            market_event=item.get("market_event") if isinstance(item.get("market_event"), Mapping) else None,
        )


@dataclass(slots=True)
class Ticker:
    market: str
    trade_price: Decimal | None = None
    signed_change_rate: Decimal | None = None
    acc_trade_price_24h: Decimal | None = None
    acc_trade_volume_24h: Decimal | None = None
    timestamp: int | None = None

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "Ticker":
        return cls(
            market=_require_str(item, "market", "Ticker"),
            trade_price=_parse_decimal_like(item.get("trade_price"), "Ticker", "trade_price"),
            signed_change_rate=_parse_decimal_like(
                item.get("signed_change_rate"),
                "Ticker",
                "signed_change_rate",
            ),
            acc_trade_price_24h=_parse_decimal_like(
                item.get("acc_trade_price_24h"),
                "Ticker",
                "acc_trade_price_24h",
            ),
            acc_trade_volume_24h=_parse_decimal_like(
                item.get("acc_trade_volume_24h"),
                "Ticker",
                "acc_trade_volume_24h",
            ),
            timestamp=_safe_int_from_any(item.get("timestamp")),
        )


@dataclass(slots=True)
class OrderbookInstrument:
    market: str
    quote_currency: str | None = None
    tick_size: Decimal | None = None
    supported_levels: list[Decimal] | None = None

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "OrderbookInstrument":
        return cls(
            market=_require_str(item, "market", "OrderbookInstrument"),
            quote_currency=_as_str(item.get("quote_currency")),
            tick_size=_parse_decimal_like(item.get("tick_size"), "OrderbookInstrument", "tick_size"),
            supported_levels=_parse_decimal_list(
                item.get("supported_levels"),
                "OrderbookInstrument",
                "supported_levels",
            ),
        )


@dataclass(slots=True)
class SupportedLevels:
    market: str
    supported_levels: list[Decimal]

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "SupportedLevels":
        levels = _parse_decimal_list(item.get("supported_levels"), "SupportedLevels", "supported_levels")
        return cls(
            market=_require_str(item, "market", "SupportedLevels"),
            supported_levels=levels or [],
        )


@dataclass(slots=True)
class OrderbookUnit:
    ask_price: Decimal
    bid_price: Decimal
    ask_size: Decimal
    bid_size: Decimal

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "OrderbookUnit":
        ask_price = _parse_decimal_like(item.get("ask_price"), "OrderbookUnit", "ask_price")
        bid_price = _parse_decimal_like(item.get("bid_price"), "OrderbookUnit", "bid_price")
        ask_size = _parse_decimal_like(item.get("ask_size"), "OrderbookUnit", "ask_size")
        bid_size = _parse_decimal_like(item.get("bid_size"), "OrderbookUnit", "bid_size")
        if ask_price is None:
            raise UpbitParseError("OrderbookUnit", "ask_price", "required numeric value is missing")
        if bid_price is None:
            raise UpbitParseError("OrderbookUnit", "bid_price", "required numeric value is missing")
        if ask_size is None:
            raise UpbitParseError("OrderbookUnit", "ask_size", "required numeric value is missing")
        if bid_size is None:
            raise UpbitParseError("OrderbookUnit", "bid_size", "required numeric value is missing")
        return cls(
            ask_price=ask_price,
            bid_price=bid_price,
            ask_size=ask_size,
            bid_size=bid_size,
        )


@dataclass(slots=True)
class Orderbook:
    market: str
    timestamp: int | None = None
    total_ask_size: Decimal | None = None
    total_bid_size: Decimal | None = None
    orderbook_units: list[OrderbookUnit] | None = None

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "Orderbook":
        units_raw = item.get("orderbook_units")
        units: list[OrderbookUnit] | None = None
        if units_raw is not None:
            units = _parse_list_of_objects(
                units_raw,
                model="Orderbook",
                field="orderbook_units",
                parser=OrderbookUnit.from_dict,
            )

        return cls(
            market=_require_str(item, "market", "Orderbook"),
            timestamp=_safe_int_from_any(item.get("timestamp")),
            total_ask_size=_parse_decimal_like(item.get("total_ask_size"), "Orderbook", "total_ask_size"),
            total_bid_size=_parse_decimal_like(item.get("total_bid_size"), "Orderbook", "total_bid_size"),
            orderbook_units=units,
        )


@dataclass(slots=True)
class Candle:
    market: str
    candle_date_time_utc: datetime | None = None
    candle_date_time_kst: datetime | None = None
    opening_price: Decimal | None = None
    high_price: Decimal | None = None
    low_price: Decimal | None = None
    trade_price: Decimal | None = None
    timestamp: int | None = None
    candle_acc_trade_price: Decimal | None = None
    candle_acc_trade_volume: Decimal | None = None
    unit: int | None = None

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "Candle":
        return cls(
            market=_require_str(item, "market", "Candle"),
            candle_date_time_utc=_parse_datetime(
                item.get("candle_date_time_utc"),
                model="Candle",
                field="candle_date_time_utc",
            ),
            candle_date_time_kst=_parse_datetime(
                item.get("candle_date_time_kst"),
                model="Candle",
                field="candle_date_time_kst",
            ),
            opening_price=_parse_decimal_like(item.get("opening_price"), "Candle", "opening_price"),
            high_price=_parse_decimal_like(item.get("high_price"), "Candle", "high_price"),
            low_price=_parse_decimal_like(item.get("low_price"), "Candle", "low_price"),
            trade_price=_parse_decimal_like(item.get("trade_price"), "Candle", "trade_price"),
            timestamp=_safe_int_from_any(item.get("timestamp")),
            candle_acc_trade_price=_parse_decimal_like(
                item.get("candle_acc_trade_price"),
                "Candle",
                "candle_acc_trade_price",
            ),
            candle_acc_trade_volume=_parse_decimal_like(
                item.get("candle_acc_trade_volume"),
                "Candle",
                "candle_acc_trade_volume",
            ),
            unit=_safe_int_from_any(item.get("unit")),
        )


@dataclass(slots=True)
class TradeTick:
    market: str
    trade_date_utc: str | None = None
    trade_time_utc: str | None = None
    timestamp: int | None = None
    trade_price: Decimal | None = None
    trade_volume: Decimal | None = None
    ask_bid: OrderSide | None = None

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "TradeTick":
        ask_bid_raw = item.get("ask_bid")
        ask_bid = _parse_order_side(ask_bid_raw) if ask_bid_raw is not None else None
        return cls(
            market=_require_str(item, "market", "TradeTick"),
            trade_date_utc=_as_str(item.get("trade_date_utc")),
            trade_time_utc=_as_str(item.get("trade_time_utc")),
            timestamp=_safe_int_from_any(item.get("timestamp")),
            trade_price=_parse_decimal_like(item.get("trade_price"), "TradeTick", "trade_price"),
            trade_volume=_parse_decimal_like(item.get("trade_volume"), "TradeTick", "trade_volume"),
            ask_bid=ask_bid,
        )


@dataclass(slots=True)
class OrderTrade:
    market: str
    uuid: str
    price: Decimal
    volume: Decimal
    funds: Decimal
    trend: "TradeTrend"
    created_at: datetime
    side: "OrderSide"

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "OrderTrade":
        return cls(
            market=_require_str(item, "market", "OrderTrade"),
            uuid=_require_str(item, "uuid", "OrderTrade"),
            price=_parse_decimal(item.get("price"), "OrderTrade", "price", required=True),
            volume=_parse_decimal(item.get("volume"), "OrderTrade", "volume", required=True),
            funds=_parse_decimal(item.get("funds"), "OrderTrade", "funds", required=True),
            trend=_parse_trade_trend(item.get("trend")),
            created_at=_parse_datetime(item.get("created_at"), model="OrderTrade", field="created_at"),
            side=_parse_order_side(item.get("side")),
        )


@dataclass(slots=True)
class Order:
    market: str
    uuid: str
    side: "OrderSide"
    ord_type: "OrderType"
    state: "OrderState"
    created_at: datetime
    price: Decimal | None = None
    volume: Decimal | None = None
    remaining_volume: Decimal | None = None
    executed_volume: Decimal | None = None
    executed_funds: Decimal | None = None
    reserved_fee: Decimal | None = None
    remaining_fee: Decimal | None = None
    paid_fee: Decimal | None = None
    locked: Decimal | None = None
    prevented_volume: Decimal | None = None
    prevented_locked: Decimal | None = None
    trades_count: int | None = None
    time_in_force: "TimeInForce | None" = None
    smp_type: "SmpType | None" = None
    identifier: str | None = None
    trades: list[OrderTrade] | None = None

    @classmethod
    def from_dict(
        cls,
        item: Mapping[str, Any],
        strict: bool = False,
        require_trades: bool = False,
    ) -> "Order":
        trades = _parse_trades(item.get("trades"), required=require_trades)

        return cls(
            market=_require_str(item, "market", "Order"),
            uuid=_require_str(item, "uuid", "Order"),
            side=_parse_order_side(item.get("side")),
            ord_type=_parse_order_type(item.get("ord_type")),
            state=_parse_order_state(item.get("state")),
            created_at=_parse_required_datetime(item.get("created_at"), model="Order", field="created_at"),
            price=_parse_decimal(item.get("price"), "Order", "price"),
            volume=_parse_decimal(item.get("volume"), "Order", "volume"),
            remaining_volume=_parse_decimal(
                item.get("remaining_volume"),
                "Order",
                "remaining_volume",
                required=strict,
            ),
            executed_volume=_parse_decimal(
                item.get("executed_volume"),
                "Order",
                "executed_volume",
                required=strict,
            ),
            executed_funds=_parse_decimal(
                item.get("executed_funds"),
                "Order",
                "executed_funds",
                required=strict,
            ),
            reserved_fee=_parse_decimal(
                item.get("reserved_fee"),
                "Order",
                "reserved_fee",
                required=strict,
            ),
            remaining_fee=_parse_decimal(
                item.get("remaining_fee"),
                "Order",
                "remaining_fee",
                required=strict,
            ),
            paid_fee=_parse_decimal(
                item.get("paid_fee"),
                "Order",
                "paid_fee",
                required=strict,
            ),
            locked=_parse_decimal(item.get("locked"), "Order", "locked", required=strict),
            prevented_volume=_parse_decimal(item.get("prevented_volume"), "Order", "prevented_volume"),
            prevented_locked=_parse_decimal(
                item.get("prevented_locked"),
                "Order",
                "prevented_locked",
                required=strict,
            ),
            trades_count=_parse_required_int(item.get("trades_count"), "Order", "trades_count")
            if strict
            else _safe_int_from_any(item.get("trades_count")),
            time_in_force=_parse_time_in_force(item.get("time_in_force")),
            smp_type=_parse_smp_type(item.get("smp_type")),
            identifier=_as_str(item.get("identifier")),
            trades=trades,
        )


@dataclass(slots=True)
class CancelOrderRef:
    uuid: str
    market: str
    identifier: str | None = None

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "CancelOrderRef":
        return cls(
            uuid=_require_str(item, "uuid", "CancelOrderRef"),
            market=_require_str(item, "market", "CancelOrderRef"),
            identifier=_as_str(item.get("identifier")),
        )


@dataclass(slots=True)
class BatchCancelSection:
    count: int
    orders: list[CancelOrderRef]

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "BatchCancelSection":
        return cls(
            count=_parse_required_int(item.get("count"), "BatchCancelSection", "count"),
            orders=_parse_list_of_objects(
                item.get("orders"),
                model="BatchCancelSection",
                field="orders",
                parser=CancelOrderRef.from_dict,
            ),
        )


@dataclass(slots=True)
class BatchCancelResult:
    success: BatchCancelSection
    failed: BatchCancelSection

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "BatchCancelResult":
        success_raw = _require_mapping(item, "success", "BatchCancelResult")
        failed_raw = _require_mapping(item, "failed", "BatchCancelResult")
        return cls(
            success=BatchCancelSection.from_dict(success_raw),
            failed=BatchCancelSection.from_dict(failed_raw),
        )


@dataclass(slots=True)
class WithdrawalAddress:
    currency: str
    net_type: str
    network_name: str
    withdraw_address: str
    secondary_address: str | None
    beneficiary_name: str | None = None
    beneficiary_company_name: str | None = None
    beneficiary_type: str | None = None
    exchange_name: str | None = None
    wallet_type: str | None = None

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "WithdrawalAddress":
        return cls(
            currency=_require_str(item, "currency", "WithdrawalAddress"),
            net_type=_require_str(item, "net_type", "WithdrawalAddress"),
            network_name=_require_str(item, "network_name", "WithdrawalAddress"),
            withdraw_address=_require_str(item, "withdraw_address", "WithdrawalAddress"),
            secondary_address=_as_str(item.get("secondary_address")),
            beneficiary_name=_as_str(item.get("beneficiary_name")),
            beneficiary_company_name=_as_str(item.get("beneficiary_company_name")),
            beneficiary_type=_as_str(item.get("beneficiary_type")),
            exchange_name=_as_str(item.get("exchange_name")),
            wallet_type=_as_str(item.get("wallet_type")),
        )


@dataclass(slots=True)
class Withdrawal:
    type: str
    uuid: str
    currency: str
    txid: str | None
    state: "WithdrawalState"
    created_at: datetime
    amount: Decimal
    fee: Decimal
    transaction_type: "TransferType"
    is_cancelable: bool
    net_type: str | None = None
    done_at: datetime | None = None

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "Withdrawal":
        return cls(
            type=_require_str(item, "type", "Withdrawal"),
            uuid=_require_str(item, "uuid", "Withdrawal"),
            currency=_require_str(item, "currency", "Withdrawal"),
            txid=_as_str(item.get("txid")),
            state=_parse_withdrawal_state(item.get("state")),
            created_at=_parse_required_datetime(item.get("created_at"), "Withdrawal", "created_at"),
            done_at=_parse_datetime(item.get("done_at"), "Withdrawal", "done_at"),
            amount=_parse_required_decimal(item.get("amount"), "Withdrawal", "amount"),
            fee=_parse_required_decimal(item.get("fee"), "Withdrawal", "fee"),
            transaction_type=_parse_transfer_type(item.get("transaction_type")),
            is_cancelable=_require_bool(item, "is_cancelable", "Withdrawal"),
            net_type=_as_str(item.get("net_type")),
        )


@dataclass(slots=True)
class DepositAvailability:
    currency: str
    net_type: str | None
    is_deposit_possible: bool
    deposit_impossible_reason: str
    minimum_deposit_amount: Decimal
    minimum_deposit_confirmations: int
    decimal_precision: int

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "DepositAvailability":
        return cls(
            currency=_require_str(item, "currency", "DepositAvailability"),
            net_type=_as_str(item.get("net_type")),
            is_deposit_possible=_require_bool(item, "is_deposit_possible", "DepositAvailability"),
            deposit_impossible_reason=_as_str(item.get("deposit_impossible_reason")) or "",
            minimum_deposit_amount=_parse_required_decimal(
                item.get("minimum_deposit_amount"),
                "DepositAvailability",
                "minimum_deposit_amount",
            ),
            minimum_deposit_confirmations=_parse_required_int(
                item.get("minimum_deposit_confirmations"),
                "DepositAvailability",
                "minimum_deposit_confirmations",
            ),
            decimal_precision=_parse_required_int(
                item.get("decimal_precision"),
                "DepositAvailability",
                "decimal_precision",
            ),
        )


@dataclass(slots=True)
class DepositAddress:
    currency: str
    net_type: str | None
    deposit_address: str | None
    secondary_address: str | None

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "DepositAddress":
        return cls(
            currency=_require_str(item, "currency", "DepositAddress"),
            net_type=_as_str(item.get("net_type")),
            deposit_address=_as_str(item.get("deposit_address")),
            secondary_address=_as_str(item.get("secondary_address")),
        )


@dataclass(slots=True)
class DepositAddressGeneration:
    address: DepositAddress | None = None
    success: bool | None = None
    message: str | None = None

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "DepositAddressGeneration":
        # API can return either generated address fields or async acknowledgement fields.
        if "deposit_address" in item or "currency" in item:
            return cls(address=DepositAddress.from_dict(item))

        success = item.get("success")
        if success is not None and not isinstance(success, bool):
            raise UpbitParseError("DepositAddressGeneration", "success", "must be bool or null")
        return cls(success=success, message=_as_str(item.get("message")))


@dataclass(slots=True)
class Deposit:
    type: str
    uuid: str
    currency: str
    txid: str | None
    state: "DepositState"
    created_at: datetime
    amount: Decimal
    fee: Decimal
    transaction_type: "TransferType"
    net_type: str | None = None
    done_at: datetime | None = None

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "Deposit":
        return cls(
            type=_require_str(item, "type", "Deposit"),
            uuid=_require_str(item, "uuid", "Deposit"),
            currency=_require_str(item, "currency", "Deposit"),
            txid=_as_str(item.get("txid")),
            state=_parse_deposit_state(item.get("state")),
            created_at=_parse_required_datetime(item.get("created_at"), "Deposit", "created_at"),
            done_at=_parse_datetime(item.get("done_at"), "Deposit", "done_at"),
            amount=_parse_required_decimal(item.get("amount"), "Deposit", "amount"),
            fee=_parse_required_decimal(item.get("fee"), "Deposit", "fee"),
            transaction_type=_parse_transfer_type(item.get("transaction_type")),
            net_type=_as_str(item.get("net_type")),
        )


@dataclass(slots=True)
class TravelRuleVasp:
    vasp_name: str
    vasp_uuid: str
    depositable: bool
    withdrawable: bool

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "TravelRuleVasp":
        return cls(
            vasp_name=_require_str(item, "vasp_name", "TravelRuleVasp"),
            vasp_uuid=_require_str(item, "vasp_uuid", "TravelRuleVasp"),
            depositable=_require_bool(item, "depositable", "TravelRuleVasp"),
            withdrawable=_require_bool(item, "withdrawable", "TravelRuleVasp"),
        )


@dataclass(slots=True)
class TravelRuleVerification:
    deposit_uuid: str
    verification_result: str
    deposit_state: "DepositState"

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "TravelRuleVerification":
        return cls(
            deposit_uuid=_require_str(item, "deposit_uuid", "TravelRuleVerification"),
            verification_result=_require_str(
                item,
                "verification_result",
                "TravelRuleVerification",
            ),
            deposit_state=_parse_deposit_state(item.get("deposit_state")),
        )


class WalletState(str, Enum):
    WORKING = "working"
    WITHDRAW_ONLY = "withdraw_only"
    DEPOSIT_ONLY = "deposit_only"
    PAUSED = "paused"
    UNSUPPORTED = "unsupported"


class BlockState(str, Enum):
    NORMAL = "normal"
    DELAYED = "delayed"
    INACTIVE = "inactive"


class OrderSide(str, Enum):
    ASK = "ask"
    BID = "bid"


class OrderType(str, Enum):
    LIMIT = "limit"
    PRICE = "price"
    MARKET = "market"
    BEST = "best"


class OrderState(str, Enum):
    WAIT = "wait"
    WATCH = "watch"
    DONE = "done"
    CANCEL = "cancel"


class TimeInForce(str, Enum):
    FOK = "fok"
    IOC = "ioc"
    POST_ONLY = "post_only"


class SmpType(str, Enum):
    REDUCE = "reduce"
    CANCEL_MAKER = "cancel_maker"
    CANCEL_TAKER = "cancel_taker"


class TradeTrend(str, Enum):
    UP = "up"
    DOWN = "down"


class TransferType(str, Enum):
    DEFAULT = "default"
    INTERNAL = "internal"


class WithdrawalState(str, Enum):
    WAITING = "WAITING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class DepositState(str, Enum):
    PROCESSING = "PROCESSING"
    ACCEPTED = "ACCEPTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    TRAVEL_RULE_SUSPECTED = "TRAVEL_RULE_SUSPECTED"
    REFUNDING = "REFUNDING"
    REFUNDED = "REFUNDED"


class ParseStrictLevel(str, Enum):
    RELAXED = "relaxed"
    STRICT = "strict"
    STRICT_WITH_TRADES = "strict_with_trades"


@dataclass(slots=True)
class ParsePolicy:
    get_order_level: ParseStrictLevel = ParseStrictLevel.STRICT_WITH_TRADES
    get_open_orders_level: ParseStrictLevel = ParseStrictLevel.RELAXED
    create_order_level: ParseStrictLevel = ParseStrictLevel.RELAXED
    cancel_order_level: ParseStrictLevel = ParseStrictLevel.RELAXED


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _safe_int_from_any(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return _safe_int(value)
    return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _require_str(item: Mapping[str, Any], key: str, model: str) -> str:
    value = item.get(key)
    if isinstance(value, str) and value:
        return value
    raise UpbitParseError(model, key, "required string is missing or empty")


def _parse_wallet_state(value: Any) -> WalletState:
    if not isinstance(value, str):
        raise UpbitParseError("ServiceStatus", "wallet_state", "must be a string")
    try:
        return WalletState(value)
    except ValueError as exc:
        raise UpbitParseError("ServiceStatus", "wallet_state", f"unknown state: {value}") from exc


def _parse_block_state(value: Any) -> BlockState | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise UpbitParseError("ServiceStatus", "block_state", "must be a string or null")
    try:
        return BlockState(value)
    except ValueError as exc:
        raise UpbitParseError("ServiceStatus", "block_state", f"unknown state: {value}") from exc


def _parse_datetime(
    value: Any,
    model: str = "ServiceStatus",
    field: str = "block_updated_at",
) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise UpbitParseError(model, field, "must be an ISO 8601 string or null")

    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise UpbitParseError(model, field, f"invalid datetime format: {value}") from exc


def _parse_required_datetime(value: Any, model: str, field: str) -> datetime:
    parsed = _parse_datetime(value, model=model, field=field)
    if parsed is None:
        raise UpbitParseError(model, field, "required datetime is missing")
    return parsed


def _parse_decimal(
    value: Any,
    model: str,
    field: str,
    required: bool = False,
) -> Decimal | None:
    if value is None:
        if required:
            raise UpbitParseError(model, field, "required decimal string is missing")
        return None
    if not isinstance(value, str):
        raise UpbitParseError(model, field, "must be a decimal string")
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise UpbitParseError(model, field, f"invalid decimal value: {value}") from exc


def _parse_decimal_like(value: Any, model: str, field: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        return _parse_decimal(value, model, field)
    raise UpbitParseError(model, field, "must be a number, decimal string, or null")


def _parse_decimal_list(value: Any, model: str, field: str) -> list[Decimal] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise UpbitParseError(model, field, "must be a list")

    parsed: list[Decimal] = []
    for idx, item in enumerate(value):
        numeric = _parse_decimal_like(item, model, f"{field}[{idx}]")
        if numeric is None:
            raise UpbitParseError(model, field, "list item must be a numeric value")
        parsed.append(numeric)
    return parsed


def _require_bool(item: Mapping[str, Any], key: str, model: str) -> bool:
    value = item.get(key)
    if isinstance(value, bool):
        return value
    raise UpbitParseError(model, key, "required bool is missing or invalid")


def _require_mapping(item: Mapping[str, Any], key: str, model: str) -> Mapping[str, Any]:
    value = item.get(key)
    if isinstance(value, Mapping):
        return value
    raise UpbitParseError(model, key, "required object is missing or invalid")


def _parse_list_of_objects(value: Any, model: str, field: str, parser: Any) -> list[Any]:
    if not isinstance(value, list):
        raise UpbitParseError(model, field, "must be a list")

    items: list[Any] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise UpbitParseError(model, field, "list item must be an object")
        items.append(parser(item))
    return items


def _parse_required_decimal(value: Any, model: str, field: str) -> Decimal:
    parsed = _parse_decimal(value, model, field, required=True)
    if parsed is None:
        raise UpbitParseError(model, field, "required decimal string is missing")
    return parsed


def _parse_order_side(value: Any) -> OrderSide:
    if not isinstance(value, str):
        raise UpbitParseError("Order", "side", "must be a string")
    try:
        return OrderSide(value)
    except ValueError as exc:
        raise UpbitParseError("Order", "side", f"unknown side: {value}") from exc


def _parse_order_type(value: Any) -> OrderType:
    if not isinstance(value, str):
        raise UpbitParseError("Order", "ord_type", "must be a string")
    try:
        return OrderType(value)
    except ValueError as exc:
        raise UpbitParseError("Order", "ord_type", f"unknown type: {value}") from exc


def _parse_order_state(value: Any) -> OrderState:
    if not isinstance(value, str):
        raise UpbitParseError("Order", "state", "must be a string")
    try:
        return OrderState(value)
    except ValueError as exc:
        raise UpbitParseError("Order", "state", f"unknown state: {value}") from exc


def _parse_time_in_force(value: Any) -> TimeInForce | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise UpbitParseError("Order", "time_in_force", "must be a string or null")
    try:
        return TimeInForce(value)
    except ValueError as exc:
        raise UpbitParseError("Order", "time_in_force", f"unknown policy: {value}") from exc


def _parse_smp_type(value: Any) -> SmpType | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise UpbitParseError("Order", "smp_type", "must be a string or null")
    try:
        return SmpType(value)
    except ValueError as exc:
        raise UpbitParseError("Order", "smp_type", f"unknown smp type: {value}") from exc


def _parse_trade_trend(value: Any) -> TradeTrend:
    if not isinstance(value, str):
        raise UpbitParseError("OrderTrade", "trend", "must be a string")
    try:
        return TradeTrend(value)
    except ValueError as exc:
        raise UpbitParseError("OrderTrade", "trend", f"unknown trend: {value}") from exc


def _parse_transfer_type(value: Any) -> TransferType:
    if not isinstance(value, str):
        raise UpbitParseError("Transfer", "transaction_type", "must be a string")
    try:
        return TransferType(value)
    except ValueError as exc:
        raise UpbitParseError(
            "Transfer",
            "transaction_type",
            f"unknown transaction type: {value}",
        ) from exc


def _parse_withdrawal_state(value: Any) -> WithdrawalState:
    if not isinstance(value, str):
        raise UpbitParseError("Withdrawal", "state", "must be a string")
    try:
        return WithdrawalState(value)
    except ValueError as exc:
        raise UpbitParseError("Withdrawal", "state", f"unknown state: {value}") from exc


def _parse_deposit_state(value: Any) -> DepositState:
    if not isinstance(value, str):
        raise UpbitParseError("Deposit", "state", "must be a string")
    try:
        return DepositState(value)
    except ValueError as exc:
        raise UpbitParseError("Deposit", "state", f"unknown state: {value}") from exc


def _parse_required_int(value: Any, model: str, field: str) -> int:
    parsed = _safe_int_from_any(value)
    if parsed is None:
        raise UpbitParseError(model, field, "required integer is missing or invalid")
    return parsed


def _parse_trades(value: Any, required: bool = False) -> list[OrderTrade] | None:
    if value is None:
        if required:
            raise UpbitParseError("Order", "trades", "required list is missing")
        return None
    if not isinstance(value, list):
        raise UpbitParseError("Order", "trades", "must be a list")

    trades: list[OrderTrade] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise UpbitParseError("Order", "trades", "list item must be an object")
        trades.append(OrderTrade.from_dict(item))
    return trades
