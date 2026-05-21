"""Shared helpers for ingest modules: config, DuckDB connection, upserts."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "tickers.yaml"
SCHEMA_PATH = REPO_ROOT / "ingest" / "schema.sql"

INTERVAL_DAILY = "1d"
INTERVAL_MINUTE = "1m"

PRICE_COLUMNS = ["ticker_id", "interval", "ts", "open", "high", "low", "close", "volume", "source"]


@dataclass(frozen=True)
class Ticker:
    id: str
    name: str
    asset_class: str          # 'crypto' | 'kr_equity' | 'us_equity'
    meta: dict[str, Any]


def load_env() -> None:
    load_dotenv(REPO_ROOT / ".env", override=False)


def load_tickers() -> list[Ticker]:
    cfg = yaml.safe_load(CONFIG_PATH.read_text())
    universe = cfg["universe"]
    out: list[Ticker] = []
    for asset_class, entries in universe.items():
        for entry in entries:
            out.append(
                Ticker(
                    id=entry["id"],
                    name=entry["name"],
                    asset_class=asset_class,
                    meta=entry,
                )
            )
    return out


def data_dir() -> Path:
    load_env()
    path = Path(os.getenv("DATA_DIR", str(REPO_ROOT / "store"))).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def connect() -> duckdb.DuckDBPyConnection:
    """Open the shared DuckDB store and ensure schema is applied."""
    db_path = data_dir() / "prices.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute(SCHEMA_PATH.read_text())
    return con


def latest_ts(con: duckdb.DuckDBPyConnection, ticker_id: str, interval: str) -> datetime | None:
    row = con.execute(
        "SELECT max(ts) FROM prices WHERE ticker_id = ? AND interval = ?",
        [ticker_id, interval],
    ).fetchone()
    return row[0] if row and row[0] else None


def upsert_prices(
    con: duckdb.DuckDBPyConnection,
    df: pd.DataFrame,
    ticker_id: str,
    interval: str,
    source: str,
) -> int:
    """Upsert OHLCV rows. `df` must have a tz-aware UTC DatetimeIndex named 'ts'
    and columns open/high/low/close/volume. Returns the number of rows written."""
    if df is None or df.empty:
        return 0

    frame = df.copy()
    frame.index = pd.to_datetime(frame.index, utc=True)
    frame = frame.rename(columns=str.lower)
    for col in ("open", "high", "low", "close", "volume"):
        if col not in frame.columns:
            frame[col] = None

    frame = frame.reset_index().rename(columns={frame.index.name or "index": "ts"})
    if "ts" not in frame.columns:
        # rename may have collapsed; recover from the first column
        frame = frame.rename(columns={frame.columns[0]: "ts"})
    frame["ts"] = pd.to_datetime(frame["ts"], utc=True).dt.tz_convert("UTC").dt.tz_localize(None)
    frame["ticker_id"] = ticker_id
    frame["interval"] = interval
    frame["source"] = source
    frame = frame[PRICE_COLUMNS]

    con.register("incoming", frame)
    con.execute(
        """
        INSERT INTO prices (ticker_id, interval, ts, open, high, low, close, volume, source)
        SELECT ticker_id, interval, ts, open, high, low, close, volume, source FROM incoming
        ON CONFLICT (ticker_id, interval, ts) DO UPDATE SET
            open = excluded.open,
            high = excluded.high,
            low = excluded.low,
            close = excluded.close,
            volume = excluded.volume,
            source = excluded.source
        """
    )
    con.unregister("incoming")
    return len(frame)


def record_state(
    con: duckdb.DuckDBPyConnection,
    ticker_id: str,
    interval: str,
    *,
    status: str,
    message: str = "",
) -> None:
    last = latest_ts(con, ticker_id, interval)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    con.execute(
        """
        INSERT INTO ingest_state (ticker_id, interval, last_ts, last_run_at, last_status, last_message)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (ticker_id, interval) DO UPDATE SET
            last_ts = excluded.last_ts,
            last_run_at = excluded.last_run_at,
            last_status = excluded.last_status,
            last_message = excluded.last_message
        """,
        [ticker_id, interval, last, now, status, message[:500]],
    )
