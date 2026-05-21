"""Run all ingesters sequentially. Intended for cron / launchd.

Usage:
    uv run python scripts/ingest_all.py
    uv run python scripts/ingest_all.py --only crypto,kr_equity
"""
from __future__ import annotations

import argparse
import sys
import time

from ingest import krx as krx_ingest
from ingest import upbit as upbit_ingest
from ingest import us_equity as us_ingest

INGESTERS = {
    "crypto": upbit_ingest.main,
    "kr_equity": krx_ingest.main,
    "us_equity": us_ingest.main,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all market data ingesters")
    parser.add_argument(
        "--only",
        default=None,
        help="Comma-separated subset of asset classes to run (crypto, kr_equity, us_equity)",
    )
    args = parser.parse_args()

    if args.only:
        selected = [s.strip() for s in args.only.split(",") if s.strip()]
        unknown = [s for s in selected if s not in INGESTERS]
        if unknown:
            print(f"[!] Unknown asset class(es): {unknown}", file=sys.stderr)
            return 2
    else:
        selected = list(INGESTERS.keys())

    exit_code = 0
    for name in selected:
        print(f"\n=== {name} ===")
        t0 = time.time()
        try:
            INGESTERS[name]()
        except Exception as exc:
            print(f"[!] {name} raised: {exc}", file=sys.stderr)
            exit_code = 1
        print(f"[{name}] done in {time.time() - t0:.1f}s")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
