# upbit-api

Unofficial Python wrapper for the Upbit Open API (REST).

> Implemented against **Upbit Open API v1.6.1**.

## Features

- Quotation API (public) endpoints
- Exchange API (private) endpoints with JWT auth (HS512)
- Upbit query_hash generation rules for GET/DELETE/POST
- Remaining-Req header parsing for rate-limit awareness
- Typed custom exceptions for API/auth/rate-limit errors
- Standard market pair format (`BTC/KRW`) — automatically converted to/from Upbit's native `KRW-BTC` format

## Market Pair Format

This wrapper uses the standard `BASE/QUOTE` format used by most exchanges worldwide:

| This wrapper | Upbit native | Meaning |
| --- | --- | --- |
| `BTC/KRW` | `KRW-BTC` | Trade BTC with KRW |
| `ETH/BTC` | `BTC-ETH` | Trade ETH with BTC |
| `BTC/USDT` | `USDT-BTC` | Trade BTC with USDT |

The conversion is handled automatically. You can also use `to_upbit_pair()` and `to_standard_pair()` helpers directly:

```python
from upbit_api import to_upbit_pair, to_standard_pair

to_upbit_pair("BTC/KRW")       # "KRW-BTC"
to_standard_pair("KRW-BTC")    # "BTC/KRW"
```

## Install

```bash
pip install upbit-api
```

## Quick Start

```python
from upbit_api import ParsePolicy, ParseStrictLevel, UpbitClient

client = UpbitClient()
markets = client.list_trading_pairs()
print(markets[:3])

print(client.list_tickers_by_pairs(["BTC/KRW", "ETH/KRW"]))
print(client.list_tickers_by_quote_currencies(["KRW", "BTC"]))

print(client.get_candles("BTC/KRW", interval="1s", count=10))
print(client.get_candles("BTC/KRW", interval="1m", count=10))
print(client.get_candles("BTC/KRW", interval="1d", count=10, converting_price_unit="KRW"))
print(client.get_candles("BTC/KRW", interval="1w", count=10))
print(client.get_candles("BTC/KRW", interval="1M", count=10))
print(client.get_candles("BTC/KRW", interval="1y", count=5))

print(client.get_orderbook(["BTC/KRW", "ETH/KRW"]))
print(client.list_orderbook_instruments(["BTC/KRW", "ETH/KRW"]))
print(client.list_orderbook_supported_levels(["BTC/KRW", "ETH/KRW"]))
print(client.recent_trades("BTC/KRW", count=20))
```

## Private API Example

```python
from upbit_api import (
    ParsePolicy,
    ParseStrictLevel,
    UpbitClient,
)

client = UpbitClient(
    access_key="YOUR_ACCESS_KEY",
    secret_key="YOUR_SECRET_KEY",
    parse_policy=ParsePolicy(
        get_order_level=ParseStrictLevel.STRICT_WITH_TRADES,
        get_open_orders_level=ParseStrictLevel.RELAXED,
        create_order_level=ParseStrictLevel.RELAXED,
        cancel_order_level=ParseStrictLevel.RELAXED,
    ),
)

# list[AccountBalance]
balances = client.get_balances()
print(balances[0].currency, balances[0].balance)

# Order
order = client.create_order(
    market="BTC/KRW",
    side="bid",
    ord_type="limit",
    volume="0.001",
    price="50000000",
)
print(order.uuid, order.state, order.remaining_volume)

# list[ServiceStatus]
service_status = client.get_service_status()
print(service_status[0].currency, service_status[0].wallet_state)

# list[ApiKeyInfo]
api_keys = client.list_api_keys()
print(api_keys[0].access_key, api_keys[0].expire_at)

# Order
order_preview = client.create_order(
    "BTC/KRW", "bid", "limit", volume="0.001", price="50000000", test=True
)
print(order_preview.uuid)

# list[Order]
closed = client.list_closed_orders(market="BTC/KRW", states=["done", "cancel"], limit=100)
print(closed[0].uuid if closed else "no closed orders")

# BatchCancelResult
batch_result = client.batch_cancel_orders(cancel_side="all", count=20, pairs="BTC/KRW,ETH/KRW")
print(batch_result.success.count, batch_result.failed.count)

# list[WithdrawalAddress]
withdrawal_addresses = client.list_withdrawal_addresses()
print(withdrawal_addresses[0].withdraw_address if withdrawal_addresses else "no address")

# DepositAvailability
deposit_info = client.get_available_deposit_info("BTC", "BTC")
print(deposit_info.currency, deposit_info.is_deposit_possible)

# DepositAddress
deposit_address = client.get_deposit_address("BTC", "BTC")
print(deposit_address.deposit_address)

# list[TravelRuleVasp]
vasps = client.list_travel_rule_vasps()
print(vasps[0].vasp_name if vasps else "no vasp")
```

`get_service_status()` returns `list[ServiceStatus]` and maps status values to enums.
`list_api_keys()` returns `list[ApiKeyInfo]` and parses `expire_at` into `datetime`.
`get_balances()` returns `list[AccountBalance]` with numeric fields as `Decimal`.
`get_order()`, `get_open_orders()`, `create_order()`, and `cancel_order()` return typed `Order`. Use `create_order(..., test=True)` for dry-run.
`list_orders_by_ids()` and `list_closed_orders()` return `list[Order]`.
`cancel_orders_by_ids()` and `batch_cancel_orders()` return `BatchCancelResult`.
`list_withdrawal_addresses()` returns `list[WithdrawalAddress]`.
`withdraw_coin()`, `withdraw_krw()`, `get_withdrawal()`, `list_withdrawals()`, and `cancel_withdrawal()` return typed `Withdrawal`/`list[Withdrawal]`.
`get_available_deposit_info()`, `create_deposit_address()`, `get_deposit_address()`, `list_deposit_addresses()`, `deposit_krw()`, `get_deposit()`, and `list_deposits()` return typed deposit models.
`list_travel_rule_vasps()`, `verify_travel_rule_by_uuid()`, and `verify_travel_rule_by_txid()` return typed travel rule models.
`parse_policy` can control strict parsing level per order endpoint.

## Quotation Return Type Map

Quotation endpoints return typed models.

| Method(s) | Return Type |
| --- | --- |
| `list_trading_pairs()` | `list[TradingPair]` |
| `list_tickers_by_pairs()`, `list_tickers_by_quote_currencies()` | `list[Ticker]` |
| `get_orderbook()` | `list[Orderbook]` |
| `list_orderbook_instruments()` | `list[OrderbookInstrument]` |
| `list_orderbook_supported_levels()` | `list[SupportedLevels]` |
| `get_candles()` | `list[Candle]` |
| `recent_trades()` | `list[TradeTick]` |

## Exchange Return Type Map

| Method(s) | Return Type |
| --- | --- |
| `get_service_status()` | `list[ServiceStatus]` |
| `list_api_keys()` | `list[ApiKeyInfo]` |
| `get_balances()` | `list[AccountBalance]` |
| `get_order()`, `get_open_orders()`, `create_order()`, `cancel_order()` | `Order` |
| `list_orders_by_ids()`, `list_closed_orders()` | `list[Order]` |
| `cancel_orders_by_ids()`, `batch_cancel_orders()` | `BatchCancelResult` |
| `list_withdrawal_addresses()` | `list[WithdrawalAddress]` |
| `withdraw_coin()`, `withdraw_krw()`, `get_withdrawal()`, `cancel_withdrawal()` | `Withdrawal` |
| `list_withdrawals()` | `list[Withdrawal]` |
| `get_available_deposit_info()` | `DepositAvailability` |
| `create_deposit_address()` | `DepositAddressGeneration` |
| `get_deposit_address()` | `DepositAddress` |
| `list_deposit_addresses()` | `list[DepositAddress]` |
| `deposit_krw()`, `get_deposit()` | `Deposit` |
| `list_deposits()` | `list[Deposit]` |
| `list_travel_rule_vasps()` | `list[TravelRuleVasp]` |
| `verify_travel_rule_by_uuid()`, `verify_travel_rule_by_txid()` | `TravelRuleVerification` |

## Package Root Imports

You can use both styles:

```python
import upbit_api

client = upbit_api.UpbitClient(access_key="YOUR_ACCESS_KEY", secret_key="YOUR_SECRET_KEY")
withdrawal: upbit_api.Withdrawal = client.get_withdrawal(uuid="WITHDRAWAL_UUID")
print(withdrawal.state)
```

```python
from upbit_api import Deposit, TravelRuleVerification, UpbitClient

client = UpbitClient(access_key="YOUR_ACCESS_KEY", secret_key="YOUR_SECRET_KEY")
deposit: Deposit = client.get_deposit(uuid="DEPOSIT_UUID")
print(deposit.amount)

result: TravelRuleVerification = client.verify_travel_rule_by_uuid(
    deposit_uuid="DEPOSIT_UUID",
    vasp_uuid="VASP_UUID",
)
print(result.verification_result)
```

The package root exports both Quotation and Exchange typed models, including:
`TradingPair`, `Ticker`, `Orderbook`, `OrderbookInstrument`, `SupportedLevels`,
`Candle`, `TradeTick`, `Order`, `OrderTrade`, `Withdrawal`, `WithdrawalAddress`,
`Deposit`, `DepositAddress`, `DepositAddressGeneration`, `DepositAvailability`,
`TravelRuleVasp`, `TravelRuleVerification`, `BatchCancelResult`, `OrderSide`,
`OrderType`, `OrderState`, `TimeInForce`, `SmpType`, `TradeTrend`, `TransferType`,
`WithdrawalState`, and `DepositState`.

## Error Handling

```python
from upbit_api import UpbitClient, UpbitAPIError, UpbitParseError, UpbitRateLimitError

client = UpbitClient()

try:
    client.list_tickers_by_pairs(["BTC/KRW"])
except UpbitRateLimitError as e:
    print("rate limit:", e)
except UpbitParseError as e:
    print("parse error:", e)
except UpbitAPIError as e:
    print("api error:", e)
```

## Tests

```bash
pytest -q
```

## Notes

- Private API calls require API key permissions and registered caller IP.
- Each authenticated request uses a unique nonce.
- `client.last_remaining_req` stores the latest parsed `Remaining-Req` value.
- This wrapper currently focuses on REST APIs.
- Quotation REST endpoints in docs are fully implemented in `UpbitClient`.
- Exchange REST endpoints in docs are fully implemented in `UpbitClient`.
