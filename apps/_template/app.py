#!/usr/bin/env python3
"""BUSY Bar App Template
Copy this template directory to apps/<your-app-slug>/ to start a new application.
"""

import time

from busybar_kit.cli import create_base_parser, setup_logging
from busybar_kit.client import get_busybar_client
from busybar_kit.draw import build_text_element, draw_display_elements

APP_NAME = "my-app-template"


def parse_args():
    parser = create_base_parser(description="BUSY Bar App Template")
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args.verbose)

    client = None if args.dry_run else get_busybar_client(explicit_host=args.host)

    elements = [
        build_text_element("Hello BUSY Bar!", id="txt1", x=36, y=4, font="normal", align="center")
    ]

    try:
        while True:
            draw_display_elements(
                client=client,
                elements=elements,
                application_name=APP_NAME,
                priority=50,
                dry_run=args.dry_run,
            )
            print("Rendered frame")

            if args.once:
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopping...")
        if not args.dry_run and client:
            try:
                client.clear_display(application_name=APP_NAME)
            except Exception:
                pass


if __name__ == "__main__":
    main()
