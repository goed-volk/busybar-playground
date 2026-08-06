import hashlib
import sys
import urllib.request
from pathlib import Path

OPENAPI_URL = "https://api.busy.app/busybar/openapi.yaml"
VENDOR_PATH = Path(__file__).resolve().parent.parent / "vendor" / "busybar-openapi" / "openapi.yaml"


def fetch_upstream_spec() -> bytes:
    req = urllib.request.Request(OPENAPI_URL, headers={"User-Agent": "BUSYBar-Kit-Sync/1.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def main() -> None:
    check_only = "--check" in sys.argv
    update = "--update" in sys.argv

    try:
        upstream_data = fetch_upstream_spec()
    except Exception as e:
        print(f"Error fetching upstream OpenAPI spec: {e}", file=sys.stderr)
        if check_only:
            sys.exit(1)
        sys.exit(1)

    if not VENDOR_PATH.exists():
        if check_only:
            print("Vendored OpenAPI spec does not exist!", file=sys.stderr)
            sys.exit(1)
        VENDOR_PATH.parent.mkdir(parents=True, exist_ok=True)
        VENDOR_PATH.write_bytes(upstream_data)
        print("Downloaded initial OpenAPI snapshot.")
        sys.exit(0)

    current_data = VENDOR_PATH.write_bytes(upstream_data) if update else VENDOR_PATH.read_bytes()

    upstream_hash = hashlib.sha256(upstream_data).hexdigest()
    current_hash = hashlib.sha256(current_data).hexdigest()

    if check_only:
        if upstream_hash != current_hash:
            print(
                "OpenAPI spec drift detected between upstream and vendored snapshot!",
                file=sys.stderr,
            )
            sys.exit(1)
        print("OpenAPI spec is up to date.")
        sys.exit(0)

    if update:
        VENDOR_PATH.write_bytes(upstream_data)
        print(f"Updated vendored OpenAPI spec (SHA256: {upstream_hash}).")


if __name__ == "__main__":
    main()
