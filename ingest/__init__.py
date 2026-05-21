"""Market data ingestion package.

Each module fetches data for one asset class and persists into the shared
DuckDB store defined in `ingest/schema.sql`. All ingesters are designed to be
idempotent and incremental: re-running them only fetches data newer than the
latest timestamp already stored.
"""
