[English](README.md) | **한국어**

# upbit-api

Upbit Open API (REST) 비공식 Python 래퍼입니다.

> **Upbit Open API v1.6.1** 기준으로 구현되었습니다.

## 주요 기능

- Quotation API (공개) 엔드포인트
- Exchange API (비공개) 엔드포인트 — JWT 인증 (HS512)
- Upbit query_hash 생성 규칙 (GET/DELETE/POST)
- Remaining-Req 헤더 파싱을 통한 요청 제한 관리
- API/인증/요청 제한 오류에 대한 타입 지정 커스텀 예외
- 표준 마켓 페어 형식 (`BTC/KRW`) — Upbit 자체 형식 `KRW-BTC`와 자동 변환

## 마켓 페어 형식

이 래퍼는 전 세계 대부분의 거래소에서 사용하는 `BASE/QUOTE` 표준 형식을 사용합니다:

| 이 래퍼 | Upbit 원본 | 의미 |
| --- | --- | --- |
| `BTC/KRW` | `KRW-BTC` | KRW로 BTC 거래 |
| `ETH/BTC` | `BTC-ETH` | BTC로 ETH 거래 |
| `BTC/USDT` | `USDT-BTC` | USDT로 BTC 거래 |

변환은 자동으로 처리됩니다. `to_upbit_pair()`와 `to_standard_pair()` 헬퍼를 직접 사용할 수도 있습니다:

```python
from upbit_api import to_upbit_pair, to_standard_pair

to_upbit_pair("BTC/KRW")       # "KRW-BTC"
to_standard_pair("KRW-BTC")    # "BTC/KRW"
```

## 설치

```bash
pip install upbit-api
```

## 빠른 시작

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

## 비공개 API 예제

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

`get_service_status()`는 `list[ServiceStatus]`를 반환하며 상태 값을 enum으로 매핑합니다.
`list_api_keys()`는 `list[ApiKeyInfo]`를 반환하며 `expire_at`을 `datetime`으로 파싱합니다.
`get_balances()`는 `list[AccountBalance]`를 반환하며 숫자 필드는 `Decimal` 타입입니다.
`get_order()`, `get_open_orders()`, `create_order()`, `cancel_order()`는 타입 지정된 `Order`를 반환합니다. `create_order(..., test=True)`로 dry-run 가능합니다.
`list_orders_by_ids()`와 `list_closed_orders()`는 `list[Order]`를 반환합니다.
`cancel_orders_by_ids()`와 `batch_cancel_orders()`는 `BatchCancelResult`를 반환합니다.
`list_withdrawal_addresses()`는 `list[WithdrawalAddress]`를 반환합니다.
`withdraw_coin()`, `withdraw_krw()`, `get_withdrawal()`, `list_withdrawals()`, `cancel_withdrawal()`은 타입 지정된 `Withdrawal`/`list[Withdrawal]`을 반환합니다.
`get_available_deposit_info()`, `create_deposit_address()`, `get_deposit_address()`, `list_deposit_addresses()`, `deposit_krw()`, `get_deposit()`, `list_deposits()`는 타입 지정된 입금 모델을 반환합니다.
`list_travel_rule_vasps()`, `verify_travel_rule_by_uuid()`, `verify_travel_rule_by_txid()`는 타입 지정된 트래블룰 모델을 반환합니다.
`parse_policy`로 주문 엔드포인트별 파싱 엄격도를 제어할 수 있습니다.

## Quotation 반환 타입 매핑

Quotation 엔드포인트는 타입 지정된 모델을 반환합니다.

| 메서드 | 반환 타입 |
| --- | --- |
| `list_trading_pairs()` | `list[TradingPair]` |
| `list_tickers_by_pairs()`, `list_tickers_by_quote_currencies()` | `list[Ticker]` |
| `get_orderbook()` | `list[Orderbook]` |
| `list_orderbook_instruments()` | `list[OrderbookInstrument]` |
| `list_orderbook_supported_levels()` | `list[SupportedLevels]` |
| `get_candles()` | `list[Candle]` |
| `recent_trades()` | `list[TradeTick]` |

## Exchange 반환 타입 매핑

| 메서드 | 반환 타입 |
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

## 패키지 루트 임포트

두 가지 스타일 모두 사용 가능합니다:

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

패키지 루트에서 Quotation과 Exchange 타입 모델을 모두 export합니다:
`TradingPair`, `Ticker`, `Orderbook`, `OrderbookInstrument`, `SupportedLevels`,
`Candle`, `TradeTick`, `Order`, `OrderTrade`, `Withdrawal`, `WithdrawalAddress`,
`Deposit`, `DepositAddress`, `DepositAddressGeneration`, `DepositAvailability`,
`TravelRuleVasp`, `TravelRuleVerification`, `BatchCancelResult`, `OrderSide`,
`OrderType`, `OrderState`, `TimeInForce`, `SmpType`, `TradeTrend`, `TransferType`,
`WithdrawalState`, `DepositState`.

## 에러 처리

```python
from upbit_api import UpbitClient, UpbitAPIError, UpbitParseError, UpbitRateLimitError

client = UpbitClient()

try:
    client.list_tickers_by_pairs(["BTC/KRW"])
except UpbitRateLimitError as e:
    print("요청 제한:", e)
except UpbitParseError as e:
    print("파싱 오류:", e)
except UpbitAPIError as e:
    print("API 오류:", e)
```

## 테스트

```bash
pytest -q
```

## 참고 사항

- 비공개 API 호출에는 API 키 권한과 등록된 IP가 필요합니다.
- 각 인증 요청은 고유한 nonce를 사용합니다.
- `client.last_remaining_req`에 가장 최근 파싱된 `Remaining-Req` 값이 저장됩니다.
- 이 래퍼는 현재 REST API만 구현됐습니다.
- 문서에 있는 Quotation REST 엔드포인트가 `UpbitClient`에 모두 구현되어 있습니다.
- 문서에 있는 Exchange REST 엔드포인트가 `UpbitClient`에 모두 구현되어 있습니다.
