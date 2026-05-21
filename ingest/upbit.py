"""Upbit OHLCV ingester for BTC-KRW and ETH-KRW.

Daily bars: full history (Upbit returns from listing date).
Minute bars: configured rolling window (configs/tickers.yaml history.intraday_days).

Public market endpoints are unauthenticated; UPBIT_* keys are only required
for private endpoints not used here.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import pyupbit
import yaml
from tenacity import retry, stop_after_attempt, wait_exponential

from ingest.common import (
    CONFIG_PATH,
    INTERVAL_DAILY,
    INTERVAL_MINUTE,
    Ticker,
    connect,
    latest_ts,
    load_tickers,
    record_state,
    upsert_prices,
)

SOURCE = "upbit"
DAILY_BATCH = 200          # pyupbit max count per call
MINUTE_BATCH = 200


def _history_cfg() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text()).get("history", {})


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=16))
def _get_ohlcv(market: str, interval: str, to: datetime | None, count: int) -> pd.DataFrame | None:
    to_str = to.strftime("%Y-%m-%d %H:%M:%S") if to else None
    return pyupbit.get_ohlcv(market, interval=interval, count=count, to=to_str)


def _fetch_loop(
    market: str,
    pyupbit_interval: str,
    *,
    start_after: datetime | None,
    max_iters: int = 200,
) -> pd.DataFrame:
    """Walk backwards in time from now until we cross `start_after` or exhaust max_iters."""
    frames: list[pd.DataFrame] = []
    cursor: datetime | None = None
    for _ in range(max_iters):
        df = _get_ohlcv(market, pyupbit_interval, to=cursor, count=DAILY_BATCH)
        if df is None or df.empty:
            break
        frames.append(df)
        oldest = df.index.min().to_pydatetime()
        if start_after is not None and oldest <= start_after:
            break
        cursor = oldest - timedelta(seconds=1)
        time.sleep(0.1)
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames).sort_index()
    combined = combined[~combined.index.duplicated(keep="last")]
    if start_after is not None:
        combined = combined[combined.index > start_after]
    return combined


def ingest_one(ticker: Ticker, con) -> dict[str, int]:
    market = ticker.meta["market"]
    cfg = _history_cfg()
    intraday_days = int(cfg.get("intraday_days", 365))
    daily_years = int(cfg.get("daily_years", 5))

    written = {INTERVAL_DAILY: 0, INTERVAL_MINUTE: 0}

    # --- daily ---
    last_daily = latest_ts(con, ticker.id, INTERVAL_DAILY)
    if last_daily is None:
        start_after = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=daily_years * 366)
    else:
        start_after = last_daily
    daily = _fetch_loop(market, "day", start_after=start_after)
    written[INTERVAL_DAILY] = upsert_prices(con, daily, ticker.id, INTERVAL_DAILY, SOURCE)
    record_state(con, ticker.id, INTERVAL_DAILY, status="ok")

    # --- minute ---
    last_min = latest_ts(con, ticker.id, INTERVAL_MINUTE)
    minute_floor = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=intraday_days)
    start_after_min = max(last_min, minute_floor) if last_min else minute_floor
    minute = _fetch_loop(market, "minute1", start_after=start_after_min, max_iters=1500)
    written[INTERVAL_MINUTE] = upsert_prices(con, minute, ticker.id, INTERVAL_MINUTE, SOURCE)
    record_state(con, ticker.id, INTERVAL_MINUTE, status="ok")

    return written


def main() -> None:
    tickers = [t for t in load_tickers() if t.asset_class == "crypto"]
    con = connect()
    try:
        for t in tickers:
            try:
                w = ingest_one(t, con)
                print(f"[upbit] {t.id}: +{w[INTERVAL_DAILY]} daily, +{w[INTERVAL_MINUTE]} minute")
            except Exception as exc:
                record_state(con, t.id, INTERVAL_DAILY, status="error", message=str(exc))
                print(f"[upbit] {t.id} FAILED: {exc}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
