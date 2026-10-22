#!/usr/bin/env python3
"""Buienradar rain alarm app for BUSY Bar.
Takes the screen only when rain is expected, displaying a 2-hour rain intensity timeline.
"""

import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

from busybar_kit.cli import create_base_parser, setup_logging
from busybar_kit.client import get_busybar_client
from busybar_kit.draw import (
    PRIORITY_NOTABLE_MIN,
    PRIORITY_URGENT_MIN,
    build_rectangle_element,
    build_text_element,
    draw_display_elements,
)
from busybar_kit.text import sanitize_text

APP_NAME = "buienradar-alarm"
BUIENRADAR_URL = "https://gpsgadget.buienradar.nl/data/raintext"


def parse_args():
    parser = create_base_parser(description="Buienradar Rain Alarm for BUSY Bar")
    parser.add_argument(
        "--lat", type=float, default=52.37, help="Latitude (default: 52.37 Amsterdam)"
    )
    parser.add_argument(
        "--lon", type=float, default=4.89, help="Longitude (default: 4.89 Amsterdam)"
    )
    parser.add_argument(
        "--refresh", type=int, default=300, help="Seconds between data fetches (default: 300)"
    )
    parser.add_argument(
        "--urgent", action="store_true", help="Raise priority to 95 to interrupt focus sessions"
    )
    parser.add_argument("--test", action="store_true", help="Run with simulated rain data")
    return parser.parse_args()


def _fetch_rain(lat: float, lon: float) -> list[tuple[int, int]]:
    url = f"{BUIENRADAR_URL}?{urllib.parse.urlencode({'lat': lat, 'lon': lon})}"
    req = urllib.request.Request(url, headers={"User-Agent": "busybar-rain-alarm/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read().decode("utf-8", "ignore")
    return _parse_rain(raw)


def _parse_rain(raw: str) -> list[tuple[int, int]]:
    now = datetime.now()
    now_minutes = now.hour * 60 + now.minute
    result = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) != 2:
            continue
        try:
            value = int(parts[0].strip())
            hh, mm = parts[1].strip().split(":")
            entry_minutes = int(hh) * 60 + int(mm)
        except (ValueError, IndexError):
            continue
        delta = entry_minutes - now_minutes
        if delta < -60:
            delta += 24 * 60
        result.append((delta, value))
    return result


def _fake_series() -> list[tuple[int, int]]:
    values = [0, 0, 40, 80, 120, 180, 220, 180, 120, 80, 40]
    series = []
    for i in range(24):
        v = values[i] if i < len(values) else 0
        series.append((i * 5, v))
    return series


def _build_headline(series: list[tuple[int, int]]) -> tuple[str | None, bool]:
    if not series:
        return None, False
    first_minutes, first_value = series[0]
    if first_value <= 0:
        for minutes, value in series:
            if value > 0:
                return sanitize_text(f"REGEN IN {max(minutes, 0)} MIN"), False
        return None, False
    else:
        for minutes, value in series:
            if minutes >= 0 and value <= 0:
                return sanitize_text(f"DROOG IN {minutes} MIN"), True
        return sanitize_text("REGEN"), True


def _bar_color(value: int) -> str:
    if value < 70:
        return "#00C8FFFF"
    if value < 150:
        return "#0064FFFF"
    return "#9600FFFF"


def _build_elements(headline: str, series: list[tuple[int, int]]) -> list:
    elements = []
    drop_color = "#00A8FFFF"
    elements.extend(
        [
            build_rectangle_element(1, 2, id="drop_tip", x=4, y=0, color=drop_color),
            build_rectangle_element(3, 1, id="drop_neck", x=3, y=2, color=drop_color),
            build_rectangle_element(5, 2, id="drop_body", x=2, y=3, color=drop_color),
            build_rectangle_element(3, 1, id="drop_base", x=3, y=5, color=drop_color),
            build_rectangle_element(1, 1, id="drop_glint", x=3, y=3, color="#B3E5FCFF"),
        ]
    )

    elements.append(
        build_text_element(
            text=headline,
            id="headline",
            x=41,
            y=-1,
            font="small",
            align="top_mid",
            color="#EAF6FFFF",
        )
    )

    elements.append(build_rectangle_element(72, 1, id="baseline", x=0, y=15, color="#102027FF"))
    for i, tick_x in enumerate((18, 36, 54)):
        elements.append(
            build_rectangle_element(1, 1, id=f"tick{i}", x=tick_x, y=15, color="#3A4A55FF")
        )

    for slot in range(24):
        value = series[slot][1] if slot < len(series) else 0
        if value <= 0:
            continue
        h = max(1, round(value / 255 * 7))
        elements.append(
            build_rectangle_element(
                2,
                h,
                id=f"bar{slot}",
                x=slot * 3,
                y=16 - h,
                color=_bar_color(value),
            )
        )

    return elements


def main():
    args = parse_args()
    setup_logging(args.verbose)

    priority = PRIORITY_URGENT_MIN + 4 if args.urgent else PRIORITY_NOTABLE_MIN + 10  # 95 vs 70

    client = None if args.dry_run else get_busybar_client(explicit_host=args.host)

    if args.test:
        series = _fake_series()
        headline, _ = _build_headline(series)
        if headline is None:
            print("test: no rain in series")
            sys.exit(0)
        elements = _build_elements(headline, series)
        draw_display_elements(
            client=client,
            elements=elements,
            application_name=APP_NAME,
            priority=priority,
            led_notification_color="#2196F3FF",
            dry_run=args.dry_run,
        )
        print(f"Test draw: '{headline}' with {len(elements)} elements (priority {priority})")
        sys.exit(0)

    print(f"Starting {APP_NAME} (priority={priority}, dry_run={args.dry_run})")

    last_fetch = 0.0
    last_clear_sent = False
    first_alert = True
    series = []

    try:
        while True:
            now = time.monotonic()
            if now - last_fetch >= args.refresh or last_fetch == 0.0:
                try:
                    series = _fetch_rain(args.lat, args.lon)
                    last_fetch = now
                except Exception as e:
                    print(f"Rain fetch error: {e}")
                    if last_fetch == 0.0:
                        last_fetch = now

            any_rain = any(v > 0 for _, v in series)

            if not any_rain:
                if not last_clear_sent:
                    if not args.dry_run and client:
                        try:
                            client.display_clear(application_name=APP_NAME)
                        except Exception as e:
                            print(f"Failed to clear display: {e}")
                    print("Dry weather: display cleared")
                    last_clear_sent = True
                    first_alert = True
            else:
                headline, _ = _build_headline(series)
                if headline:
                    elements = _build_elements(headline, series)
                    led_color = "#2196F3FF" if first_alert else None
                    success = draw_display_elements(
                        client=client,
                        elements=elements,
                        application_name=APP_NAME,
                        priority=priority,
                        led_notification_color=led_color,
                        dry_run=args.dry_run,
                    )
                    if success:
                        first_alert = False
                        last_clear_sent = False
                        print(f"Drew rain alert: '{headline}' ({len(elements)} elements)")

            if args.once:
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopping...")
        if not args.dry_run and client:
            try:
                client.display_clear(application_name=APP_NAME)
            except Exception:
                pass


if __name__ == "__main__":
    main()
