"""US equity OHLCV ingester for GOOGL and NVDA via yfinance.

Daily bars: full configured history.
Minute bars: yfinance caps 1-minute interval at ~7 trailing days per call,
so this run captures only the most recent week — sufficient for daily refresh.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import yaml
import yfinance as yf
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

SOURCE = "yfinance"


def _history_cfg() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text()).get("history", {})


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    out = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
    out.index = pd.to_datetime(out.index, utc=True)
    return out


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=16))
def _yf_download(ticker: str, *, start: str | None = None, period: str | None = None, interval: str) -> pd.DataFrame:
    if period:
        return yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    return yf.download(ticker, start=start, interval=interval, progress=False, auto_adjust=False)


def ingest_one(ticker: Ticker, con) -> dict[str, int]:
    cfg = _history_cfg()
    daily_years = int(cfg.get("daily_years", 5))

    written = {INTERVAL_DAILY: 0, INTERVAL_MINUTE: 0}

    # --- daily ---
    last_daily = latest_ts(con, ticker.id, INTERVAL_DAILY)
    if last_daily is None:
        start = (datetime.now(timezone.utc) - timedelta(days=daily_years * 366)).strftime("%Y-%m-%d")
    else:
        start = (last_daily + timedelta(days=1)).strftime("%Y-%m-%d")
    raw_daily = _yf_download(ticker.meta["ticker_yf"], start=start, interval="1d")
    daily = _normalize(raw_daily)
    written[INTERVAL_DAILY] = upsert_prices(con, daily, ticker.id, INTERVAL_DAILY, SOURCE)
    record_state(con, ticker.id, INTERVAL_DAILY, status="ok")

    # --- minute (yfinance trailing 7 days) ---
    raw_min = _yf_download(ticker.meta["ticker_yf"], period="7d", interval="1m")
    minute = _normalize(raw_min)
    last_min = latest_ts(con, ticker.id, INTERVAL_MINUTE)
    if last_min is not None and not minute.empty:
        minute = minute[minute.index > pd.Timestamp(last_min, tz="UTC")]
    written[INTERVAL_MINUTE] = upsert_prices(con, minute, ticker.id, INTERVAL_MINUTE, SOURCE)
    record_state(con, ticker.id, INTERVAL_MINUTE, status="ok")

    return written


def main() -> None:
    tickers = [t for t in load_tickers() if t.asset_class == "us_equity"]
    con = connect()
    try:
        for t in tickers:
            try:
                w = ingest_one(t, con)
                print(f"[us_equity] {t.id}: +{w[INTERVAL_DAILY]} daily, +{w[INTERVAL_MINUTE]} minute")
            except Exception as exc:
                record_state(con, t.id, INTERVAL_DAILY, status="error", message=str(exc))
                print(f"[us_equity] {t.id} FAILED: {exc}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
