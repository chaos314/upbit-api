"""Upbit API example script.

Usage:
    1. Set your API keys in .env:
       UPBIT_ACCESS_KEY=your_access_key
       UPBIT_SECRET_KEY=your_secret_key

    2. Run:
       python example.py
"""

import os
from dotenv import load_dotenv
from upbit_api import UpbitClient, UpbitAPIError

load_dotenv()


def test_public_api(client: UpbitClient):
    """Public API (no key required)"""
    print("=" * 50)
    print("Public API Test")
    print("=" * 50)

    # Trading pairs
    markets = client.list_trading_pairs()
    krw_markets = [m for m in markets if m.market.startswith("KRW-")]
    print(f"\nKRW markets: {len(krw_markets)}")
    for m in krw_markets[:5]:
        print(f"  {m.market}: {m.korean_name}")

    # BTC, ETH current price
    tickers = client.list_tickers_by_pairs(["KRW-BTC", "KRW-ETH"])
    print("\nCurrent prices:")
    for t in tickers:
        print(f"  {t.market}: {t.trade_price:,.0f} KRW ({t.signed_change_rate * 100:+.2f}%)")

    # BTC orderbook
    orderbooks = client.get_orderbook(["KRW-BTC"])
    ob = orderbooks[0]
    print(f"\nBTC orderbook (best ask: {ob.orderbook_units[0].ask_price:,.0f}, best bid: {ob.orderbook_units[0].bid_price:,.0f})")

    # BTC recent trades
    trades = client.recent_trades("KRW-BTC", count=5)
    print("\nBTC recent trades:")
    for t in trades:
        print(f"  {t.trade_time_utc} | {t.trade_price:,.0f} KRW | {t.trade_volume} BTC")


def test_private_api(client: UpbitClient):
    """Private API (key required)"""
    print("\n" + "=" * 50)
    print("Private API Test")
    print("=" * 50)

    # Balances
    balances = client.get_balances()
    print("\nBalances:")
    for b in balances:
        if float(b.balance) > 0:
            print(f"  {b.currency}: {b.balance} (avg buy price: {b.avg_buy_price})")

    # API key info
    api_keys = client.list_api_keys()
    print(f"\nAPI keys: {len(api_keys)}")
    for k in api_keys:
        print(f"  {k.access_key[:8]}... | expires: {k.expire_at}")

    # Service status
    statuses = client.get_service_status()
    print(f"\nService status ({len(statuses)} coins):")
    for s in statuses[:5]:
        print(f"  {s.currency}: {s.wallet_state}")


def main():
    access_key = os.getenv("UPBIT_ACCESS_KEY")
    secret_key = os.getenv("UPBIT_SECRET_KEY")

    client = UpbitClient(access_key=access_key, secret_key=secret_key)

    try:
        test_public_api(client)
    except UpbitAPIError as e:
        print(f"Public API error: {e}")

    if access_key and secret_key:
        try:
            test_private_api(client)
        except UpbitAPIError as e:
            print(f"Private API error: {e}")
    else:
        print("\nNo API keys found in .env — skipping Private API test.")


if __name__ == "__main__":
    main()
