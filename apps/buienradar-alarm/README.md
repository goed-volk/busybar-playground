# Buienradar Rain Alarm App

Takes the BUSY Bar screen only when rain is expected in your location, displaying a 2-hour rain intensity timeline.

## Usage
```bash
python3 apps/buienradar-alarm/app.py [--lat 52.37] [--lon 4.89] [--urgent] [--dry-run]
```

- `--lat`, `--lon`: Coordinates (default: Amsterdam 52.37, 4.89).
- `--urgent`: Boosts priority to 95 to interrupt active focus sessions.
- `--dry-run`: Runs data fetching and log output without drawing to hardware.
- `--test`: Renders sample rain timeline data once.
