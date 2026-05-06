"""Command-line interface for DriftWatch."""
from __future__ import annotations

import argparse
import logging
import sys
import time

from driftwatch.config import ConfigError, load_config
from driftwatch.engine import Engine

logger = logging.getLogger("driftwatch")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        level=level,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="driftwatch",
        description="Detect infrastructure configuration drift.",
    )
    parser.add_argument("config", help="Path to YAML/JSON config file.")
    parser.add_argument(
        "--interval",
        type=float,
        default=0,
        metavar="SECONDS",
        help="Poll interval in seconds (0 = run once and exit).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        return 1

    engine = Engine(config)
    engine.capture_baseline()
    logger.info("DriftWatch started. Interval=%ss", args.interval or "one-shot")

    if args.interval <= 0:
        events = engine.run_cycle()
        logger.info("Cycle complete. %d drift event(s) detected.", len(events))
        return 0

    try:
        while True:
            time.sleep(args.interval)
            events = engine.run_cycle()
            logger.info("Cycle complete. %d drift event(s) detected.", len(events))
    except KeyboardInterrupt:
        logger.info("DriftWatch stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
