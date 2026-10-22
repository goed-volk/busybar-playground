# Display Elements Specification

BUSY Bar supports five distinct display element types rendered on the LED matrix or OLED screen.

## Element Types

### 1. `text`
- **Purpose**: Render printable ASCII text strings.
- **Constraints**:
  - `text`: Must contain **printable ASCII only** (`^[\x20-\x7E]+$`). Non-ASCII characters (e.g. `ë`, `€`, emoji) must be sanitized or transliterated before draw.
  - `font`: One of `tiny`, `small`, `normal`, `condensed`, `bold`, `large`, `extra_large`, `global`.
  - `align`: One of `top_left`, `top_mid`, `top_right`, `mid_left`, `center`, `mid_right`, `bottom_left`, `bottom_mid`, `bottom_right`.
  - `color`: `#RRGGBBAA` hex color string (e.g., `#FFFFFFFF`).
  - `x`, `y`: Integer offset coordinates in range `[-4096, 4095]`.

### 2. `image`
- **Purpose**: Display static images (PNG/BMP) from storage or stock icon catalog.
- **Fields**:
  - `path`: Path to image file stored in internal device storage (e.g., `/ext/apps/my_app/icon.png`).
  - `stock_path`: Path to built-in stock icon (`shared/[a-z0-9_.]+$`). Note: The stock icon catalog is not formally enumerated in the official API spec.

### 3. `animation`
- **Purpose**: Display animated graphics (GIF/SND/custom animations).
- **Fields**:
  - `path`: Path to animation file in device storage.
  - `loop`: Boolean indicating whether animation should loop continuously.

### 4. `countdown`
- **Purpose**: Live countdown or timer display.
- **Fields**:
  - `timestamp`: ISO 8601 string or Unix timestamp.
  - `direction`: `time_left` or `time_since`.
  - `show_hours`: `when_non_zero` or `always`.

### 5. `rectangle`
- **Purpose**: Geometric rectangle shapes and background fills.
- **Fields (OpenAPI 27.5.0 & `busylib 2.6.1`)**:
  - `width`, `height`: Integer dimensions in pixels (`gt: 0`).
  - `radius`: Corner border radius in pixels (`ge: 0`, default: `0`).
  - `fill`: Fill style: `none`, `solid`, `gradient_h`, `gradient_v` (default: `none`).
  - `fill_colors`: List of 1 to 2 `#RRGGBBAA` hex color strings (default: `["#FFFFFFFF", "#00000000"]`).
  - `border_width`: Integer border stroke width in pixels (`ge: 0`, default: `1`).
  - `border_color`: `#RRGGBBAA` hex color string (default: `#FFFFFFFF`).
- **Kit Helper**: `busybar_kit.draw.build_rectangle_element` accepts `color` as an ergonomic shortcut, automatically setting `fill_colors=[color]` and `border_color=color` with `border_width=0` and `fill="solid"`.

---

## Screen Canvas Specs

- **Front Display**: **72 × 16 RGB LED Matrix**, 2.2 mm pitch, 60 Hz max refresh.
- **Back Display**: **160 × 80 Monochrome OLED**, 16 grayscale levels (SSD1320 controller).
