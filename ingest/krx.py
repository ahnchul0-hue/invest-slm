"""Korean equity OHLCV ingester for 005930 (Samsung Electronics) and 000660 (SK hynix).

Sources:
  - Daily bars: pykrx (KRX official aggregates)
  - Minute bars: yfinance (KRX doesn't expose intraday for free; yfinance covers
    the last ~30 days at 1-minute resolution under the .KS symbol)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import yaml
import yfinance as yf
from pykrx import stock
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

SOURCE_DAILY = "pykrx"
SOURCE_MINUTE = "yfinance"
KRX_TZ = "Asia/Seoul"


def _history_cfg() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text()).get("history", {})


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=16))
def _pykrx_daily(ticker_krx: str, start: str, end: str) -> pd.DataFrame:
    return stock.get_market_ohlcv_by_date(start, end, ticker_krx)


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=16))
def _yf_minute(ticker_yf: str, period: str = "7d") -> pd.DataFrame:
    return yf.download(ticker_yf, period=period, interval="1m", progress=False, auto_adjust=False)


def _normalize_pykrx(df: pd.DataFrame) -> pd.DataFrame:
    """pykrx returns columns ['시가','고가','저가','종가','거래량'] with KST date index."""
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.rename(
        columns={"시가": "open", "고가": "high", "저가": "low", "종가": "close", "거래량": "volume"}
    )
    # Date index → midnight KST → UTC
    out.index = pd.to_datetime(out.index).tz_localize(KRX_TZ).tz_convert("UTC")
    return out[["open", "high", "low", "close", "volume"]]


def _normalize_yf(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    out = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
    out.index = pd.to_datetime(out.index, utc=True)
    return out


def ingest_one(ticker: Ticker, con) -> dict[str, int]:
    cfg = _history_cfg()
    daily_years = int(cfg.get("daily_years", 5))

    written = {INTERVAL_DAILY: 0, INTERVAL_MINUTE: 0}

    # --- daily (pykrx) ---
    last_daily = latest_ts(con, ticker.id, INTERVAL_DAILY)
    if last_daily is None:
        start_dt = datetime.now(timezone.utc) - timedelta(days=daily_years * 366)
    else:
        start_dt = (last_daily.replace(tzinfo=timezone.utc)) + timedelta(days=1)
    end_dt = datetime.now(timezone.utc) + timedelta(days=1)
    start_str = start_dt.strftime("%Y%m%d")
    end_str = end_dt.strftime("%Y%m%d")

    raw_daily = _pykrx_daily(ticker.meta["ticker_krx"], start_str, end_str)
    daily = _normalize_pykrx(raw_daily)
    written[INTERVAL_DAILY] = upsert_prices(con, daily, ticker.id, INTERVAL_DAILY, SOURCE_DAILY)
    record_state(con, ticker.id, INTERVAL_DAILY, status="ok")

    # --- minute (yfinance, last ~7d) ---
    raw_min = _yf_minute(ticker.meta["ticker_yf"], period="7d")
    minute = _normalize_yf(raw_min)
    last_min = latest_ts(con, ticker.id, INTERVAL_MINUTE)
    if last_min is not None and not minute.empty:
        minute = minute[minute.index > pd.Timestamp(last_min, tz="UTC")]
    written[INTERVAL_MINUTE] = upsert_prices(con, minute, ticker.id, INTERVAL_MINUTE, SOURCE_MINUTE)
    record_state(con, ticker.id, INTERVAL_MINUTE, status="ok")

    return written


def main() -> None:
    tickers = [t for t in load_tickers() if t.asset_class == "kr_equity"]
    con = connect()
    try:
        for t in tickers:
            try:
                w = ingest_one(t, con)
                print(f"[krx] {t.id}: +{w[INTERVAL_DAILY]} daily, +{w[INTERVAL_MINUTE]} minute")
            except Exception as exc:
                record_state(con, t.id, INTERVAL_DAILY, status="error", message=str(exc))
                print(f"[krx] {t.id} FAILED: {exc}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
