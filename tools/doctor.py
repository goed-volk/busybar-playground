#!/usr/bin/env python3
"""BUSY Bar Environment Doctor
Probes local environment, venv, device registry, and reachable devices over Wi-Fi/USB.
"""

import sys
from importlib.metadata import version

from busylib.versioning import API_VERSION

from busybar_kit.config import load_config
from busybar_kit.resolve import is_device_reachable


def main():
    print("=== BUSY Bar Doctor ===")
    print(f"Python Version: {sys.version.split()[0]}")
    try:
        busylib_ver = version("busylib")
    except Exception:
        busylib_ver = "unknown"
    print(f"busylib Version: {busylib_ver}")
    print(f"Target API Semver: {API_VERSION}")
    print()

    try:
        config = load_config()
        print(f"Loaded Device Config: '{config.name}' (Label: '{config.label}')")
        print(f"  - Config File: {config.source or 'None (USB default)'}")
        print(f"  - Wi-Fi Host: {config.wifi_host or 'None'}")
        print(f"  - USB Host:   {config.usb_host or 'None'}")
        print(f"  - Preferred:  {config.prefer}")
        print(f"  - Token Env:  {config.token_env} ({'Set' if config.token else 'NOT Set'})")

        print("\nProbing Connection Candidates:")
        if config.wifi_host:
            wifi_ok = is_device_reachable(config.wifi_host)
            status_str = "REACHABLE" if wifi_ok else "UNREACHABLE / Wi-Fi API Disabled (403)"
            print(f"  - Wi-Fi ({config.wifi_host}): {status_str}")
        if config.usb_host:
            usb_ok = is_device_reachable(config.usb_host)
            print(f"  - USB ({config.usb_host}):   {'REACHABLE' if usb_ok else 'UNREACHABLE'}")

    except Exception as e:
        print(f"Device Config Info: {e}")

    print("\nDoctor check completed.")


if __name__ == "__main__":
    main()
