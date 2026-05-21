-- DuckDB schema for invest-slm market data store.
-- Loaded by ingest.common.connect() on every run; statements are idempotent.

-- Unified OHLCV table for all asset classes.
-- ts is stored as UTC; the display tier converts to KST.
CREATE TABLE IF NOT EXISTS prices (
    ticker_id   VARCHAR NOT NULL,        -- matches configs/tickers.yaml `id`
    interval    VARCHAR NOT NULL,        -- '1d' | '1m'
    ts          TIMESTAMP NOT NULL,      -- bar open time, UTC
    open        DOUBLE,
    high        DOUBLE,
    low         DOUBLE,
    close       DOUBLE,
    volume      DOUBLE,
    source      VARCHAR NOT NULL,        -- 'upbit' | 'pykrx' | 'yfinance' | ...
    ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker_id, interval, ts)
);

CREATE INDEX IF NOT EXISTS idx_prices_ticker_ts ON prices (ticker_id, ts DESC);

-- Per-ticker ingest watermarks, used for incremental fetches.
CREATE TABLE IF NOT EXISTS ingest_state (
    ticker_id     VARCHAR NOT NULL,
    interval      VARCHAR NOT NULL,
    last_ts       TIMESTAMP,             -- latest bar successfully stored (UTC)
    last_run_at   TIMESTAMP,
    last_status   VARCHAR,               -- 'ok' | 'error'
    last_message  VARCHAR,
    PRIMARY KEY (ticker_id, interval)
);
