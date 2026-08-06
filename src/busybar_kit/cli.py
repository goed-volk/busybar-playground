import argparse
import logging
import sys


def create_base_parser(description: str = "BUSY Bar Application") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Device name from config/devices.toml (or BUSYBAR_DEVICE env var)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Explicit host/IP override (e.g. 192.168.1.42 or 10.0.4.20)",
    )
    parser.add_argument(
        "--token-env",
        type=str,
        default=None,
        help="Environment variable name holding the device API token",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform configuration and resolution without sending writes to device",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single update cycle and exit",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Polling interval in seconds when running continuously (default: 60)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    return parser


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
