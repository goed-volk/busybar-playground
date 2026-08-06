# Matter Smart Home Specification

## Overview
BUSY Bar includes Matter smart home protocol support over Wi-Fi.

- **Device Endpoint Type**: Binary Light / On-Off Light Switch (`ON` when a timer or focus session is running; `OFF` when idle).
- **Multi-Fabric**: Supports commissioning across multiple Matter fabrics simultaneously (e.g. Google Home and Apple Home).
- **Confirmed Compatibility**: Tested and confirmed working with Google TV Streamer (4K) as Matter hub.
- **Exclusions**: Matter protocol specification does not convey display elements, battery percentages, or API tokens.
