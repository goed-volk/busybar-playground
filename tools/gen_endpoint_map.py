from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "vendor" / "busybar-openapi" / "openapi.yaml"
OUTPUT_PATH = ROOT / "docs" / "api" / "endpoint-map.md"


def main() -> None:
    if not SPEC_PATH.exists():
        print(f"Spec not found at {SPEC_PATH}")
        return

    with open(SPEC_PATH, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    lines = [
        "# OpenAPI Endpoint Map",
        "",
        "*THIS FILE IS GENERATED AUTOMATICALLY BY `tools/gen_endpoint_map.py`.*",
        "",
        "Note: Spec declares `/busybar/...` path prefix (`servers: [/]`). "
        "On-device HTTP server serves the same paths under `/api/...`. "
        "Device-local routes (e.g. `/api/apps/launch`, `/api/apps/quit`) execute exclusively "
        "on device hardware and are omitted from this cloud proxy snapshot.",
        "",
        "| Spec Path | Method | Operation ID | Summary |",
        "|---|---|---|---|",
    ]

    paths = spec.get("paths", {})
    for path, methods in sorted(paths.items()):
        for method, info in sorted(methods.items()):
            if method not in ("get", "post", "put", "delete", "patch"):
                continue
            op_id = info.get("operationId", "")
            summary = info.get("summary", "").replace("|", "\\|")
            lines.append(f"| `{path}` | **{method.upper()}** | `{op_id}` | {summary} |")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
