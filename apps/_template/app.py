#!/usr/bin/env python3
"""BUSY Bar App Template
Copy this template directory to apps/<your-app-slug>/ to start a new application.
"""

import logging
import signal
import threading

from busybar_kit.cli import create_base_parser, setup_logging
from busybar_kit.client import DeviceError, DeviceSession
from busybar_kit.config import load_app_config
from busybar_kit.draw import PRIORITY_INFO_DEFAULT, DrawResult, build_text_element
from busybar_kit.resolve import resolve_device

APP_NAME = "my-app-template"
MAX_ERROR_BACKOFF = 300.0

logger = logging.getLogger(APP_NAME)


def main() -> None:
    args = create_base_parser(description="BUSY Bar App Template").parse_args()
    redaction = setup_logging(args.verbose)

    app = load_app_config()
    device = app.device(args.device)
    token = app.token_for(device)
    redaction.add(token)
    resolution = resolve_device(device, token, explicit_host=args.host)
    logger.info("Device '%s' at %s (%s)", device.name, resolution.host, resolution.source)

    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())

    elements = [build_text_element("Hello BUSY Bar!", id="txt1", x=36, y=4, align="center")]

    with DeviceSession(
        resolution, application_name=APP_NAME, dry_run=args.dry_run, cancel=stop
    ) as session:
        error_backoff = float(args.interval)
        try:
            while not stop.is_set():
                wait = float(args.interval)
                try:
                    result = session.draw(elements, priority=PRIORITY_INFO_DEFAULT)
                    logger.info("Frame: %s", result.value)
                    error_backoff = float(args.interval)
                    if result is DrawResult.CANCELLED:
                        break
                except DeviceError as e:
                    logger.warning("Draw failed: %s", e)
                    wait = error_backoff
                    error_backoff = min(error_backoff * 2, MAX_ERROR_BACKOFF)

                if args.once:
                    break
                stop.wait(wait)
        except KeyboardInterrupt:
            stop.set()
        finally:
            if not args.once:
                session.clear()


if __name__ == "__main__":
    main()
