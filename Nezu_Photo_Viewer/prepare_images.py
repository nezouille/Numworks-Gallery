import argparse
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps

SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
WIDTH, HEIGHT = 320, 240
THUMB_WIDTH, THUMB_HEIGHT = 96, 72
GRID_COLUMNS, GRID_ROWS = 3, 3
CELL_WIDTH, CELL_HEIGHT = THUMB_WIDTH + 2, THUMB_HEIGHT + 1
GRID_OFFSET_X = (WIDTH - GRID_COLUMNS * CELL_WIDTH) // 2
FOOTER_HEIGHT = 20


def natural_key(path: Path):
    return [int(part) if part.isdigit() else part.casefold()
            for part in re.split(r"(\d+)", path.name)]


def rgb565_bytes(image: Image.Image) -> bytes:
    width, height = image.size
    pixels = image.load()
    out = bytearray(width * height * 2)
    offset = 0
    for y in range(height):
        for x in range(width):
            red, green, blue = pixels[x, y]
            value = ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)
            out[offset] = value & 0xFF
            out[offset + 1] = value >> 8
            offset += 2
    return bytes(out)


def prepare(source: Path, output: Path, icon_path: Path):
    files = sorted((p for p in source.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED), key=natural_key)
    if not files:
        raise SystemExit("No PNG, JPG, WEBP, or BMP images were found in this folder.")
    output.mkdir(parents=True, exist_ok=True)

    data_path = output / "images.rgb565"
    full_images_path = output / "full_images.tmp"
    thumbnails_path = output / "thumbnails.tmp"
    with full_images_path.open("wb") as data, thumbnails_path.open("wb") as thumbnails:
        for path in files:
            with Image.open(path) as original:
                image = ImageOps.exif_transpose(original).convert("RGBA")
                white = Image.new("RGBA", image.size, (255, 255, 255, 255))
                image = Image.alpha_composite(white, image).convert("RGB")
                fitted = ImageOps.contain(image, (WIDTH, HEIGHT), Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (WIDTH, HEIGHT), "white")
                canvas.paste(fitted, ((WIDTH - fitted.width) // 2, (HEIGHT - fitted.height) // 2))
                data.write(rgb565_bytes(canvas))
                thumbnails.write(rgb565_bytes(canvas.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.Resampling.LANCZOS)))
            print(f"Added: {path.name}")

    with data_path.open("wb") as combined:
        with full_images_path.open("rb") as full_images:
            shutil.copyfileobj(full_images, combined)
        with thumbnails_path.open("rb") as thumbnails:
            shutil.copyfileobj(thumbnails, combined)
    full_images_path.unlink()
    thumbnails_path.unlink()

    with Image.open(icon_path) as original_icon:
        icon = ImageOps.fit(ImageOps.exif_transpose(original_icon).convert("RGBA"), (55, 56), method=Image.Resampling.LANCZOS)
        background = Image.new("RGBA", icon.size, (255, 255, 255, 255))
        Image.alpha_composite(background, icon).convert("RGB").save(output / "icon.png")

    count = len(files)
    (output / "main.c").write_text(f'''#include <eadk.h>

#define IMAGE_COUNT {count}
#define PIXELS_PER_IMAGE (EADK_SCREEN_WIDTH * EADK_SCREEN_HEIGHT)
#define THUMB_WIDTH {THUMB_WIDTH}
#define THUMB_HEIGHT {THUMB_HEIGHT}
#define THUMBNAIL_PIXELS ({THUMB_WIDTH} * {THUMB_HEIGHT})
#define GRID_COLUMNS {GRID_COLUMNS}
#define GRID_ROWS {GRID_ROWS}
#define CELLS_PER_PAGE (GRID_COLUMNS * GRID_ROWS)
#define CELL_WIDTH {CELL_WIDTH}
#define CELL_HEIGHT {CELL_HEIGHT}
#define GRID_OFFSET_X {GRID_OFFSET_X}
#define FOOTER_HEIGHT {FOOTER_HEIGHT}
#define FOOTER_Y (EADK_SCREEN_HEIGHT - FOOTER_HEIGHT)

const char eadk_app_name[] __attribute__((section(".rodata.eadk_app_name"))) = "Gallery";
const uint32_t eadk_api_level __attribute__((section(".rodata.eadk_api_level"))) = 0;
extern const eadk_color_t image_data[];

static uint32_t current_image = 0;
static uint8_t code_progress = 0;
static bool easter_egg_visible = false;
static bool easter_return_to_grid = true;
static bool grid_mode = true;
static const char easter_egg_text[] = "https://www.youtube.com/@Nezouillee";
static const char grid_help_text[] = "ARROWS Navigate    OK Select";
static const eadk_color_t color_numworks_yellow = 0xFF00;
static const eadk_color_t color_grid_background = 0xEF7D;
static const eadk_color_t color_footer_gray = 0xC618;

static const eadk_color_t * thumbnail_data(uint32_t image_index) {{
  return image_data + IMAGE_COUNT * PIXELS_PER_IMAGE + image_index * THUMBNAIL_PIXELS;
}}

static void show_image(void) {{
  eadk_display_push_rect(eadk_screen_rect, image_data + current_image * PIXELS_PER_IMAGE);
}}

static void show_grid(void) {{
  const uint32_t first_image = (current_image / CELLS_PER_PAGE) * CELLS_PER_PAGE;
  eadk_display_push_rect_uniform(eadk_screen_rect, color_grid_background);
  for (uint32_t slot = 0; slot < CELLS_PER_PAGE; slot++) {{
    const uint32_t image_index = first_image + slot;
    if (image_index >= IMAGE_COUNT) {{
      break;
    }}
    const uint16_t x = GRID_OFFSET_X + (slot % GRID_COLUMNS) * CELL_WIDTH + 1;
    const uint16_t y = (slot / GRID_COLUMNS) * CELL_HEIGHT + 1;
    const bool selected = image_index == current_image;
    eadk_display_push_rect((eadk_rect_t){{x, y, {THUMB_WIDTH}, {THUMB_HEIGHT}}}, thumbnail_data(image_index));
    if (selected) {{
      eadk_display_push_rect_uniform((eadk_rect_t){{x, y, THUMB_WIDTH, 2}}, color_numworks_yellow);
      eadk_display_push_rect_uniform((eadk_rect_t){{x, y + THUMB_HEIGHT - 2, THUMB_WIDTH, 2}}, color_numworks_yellow);
      eadk_display_push_rect_uniform((eadk_rect_t){{x, y, 2, THUMB_HEIGHT}}, color_numworks_yellow);
      eadk_display_push_rect_uniform((eadk_rect_t){{x + THUMB_WIDTH - 2, y, 2, THUMB_HEIGHT}}, color_numworks_yellow);
    }}
  }}
  eadk_display_push_rect_uniform((eadk_rect_t){{0, FOOTER_Y, EADK_SCREEN_WIDTH, FOOTER_HEIGHT}}, color_footer_gray);
  const uint16_t help_width = (sizeof(grid_help_text) - 1) * 7;
  eadk_display_draw_string(grid_help_text, (eadk_point_t){{(EADK_SCREEN_WIDTH - help_width) / 2, FOOTER_Y + 5}}, false, eadk_color_black, color_footer_gray);
}}

static void show_easter_egg(void) {{
  const uint16_t text_width = (sizeof(easter_egg_text) - 1) * 7;
  const uint16_t x = (EADK_SCREEN_WIDTH - text_width) / 2;
  const uint16_t y = (EADK_SCREEN_HEIGHT - 14) / 2;
  easter_return_to_grid = grid_mode;
  eadk_display_push_rect_uniform(eadk_screen_rect, eadk_color_white);
  eadk_display_draw_string(easter_egg_text, (eadk_point_t){{x, y}}, false, eadk_color_black, eadk_color_white);
  easter_egg_visible = true;
}}

static bool check_secret_code(eadk_event_t event) {{
  static const eadk_event_t sequence[] = {{
    eadk_event_eight,
    eadk_event_comma,
    eadk_event_plus,
    eadk_event_multiplication
  }};
  if (event == sequence[code_progress]) {{
    code_progress++;
    if (code_progress == sizeof(sequence) / sizeof(sequence[0])) {{
      code_progress = 0;
      show_easter_egg();
      return true;
    }}
  }} else {{
    code_progress = (event == sequence[0]) ? 1 : 0;
  }}
  return false;
}}

int main(int argc, char * argv[]) {{
  (void)argc;
  (void)argv;
  show_grid();
  uint64_t previous_loop_time = eadk_timing_millis();
  while (true) {{
    if (eadk_keyboard_key_down(eadk_keyboard_scan(), eadk_key_on_off)) {{
      return 0;
    }}
    int32_t timeout = 1000;
    eadk_event_t event = eadk_event_get(&timeout);
    uint64_t current_loop_time = eadk_timing_millis();
    if (current_loop_time < previous_loop_time || current_loop_time - previous_loop_time > 5000) {{
      return 0;
    }}
    previous_loop_time = current_loop_time;
    if (eadk_keyboard_key_down(eadk_keyboard_scan(), eadk_key_on_off)) {{
      return 0;
    }}
    if (check_secret_code(event)) {{
      continue;
    }}
    if (easter_egg_visible) {{
      if (event == eadk_event_left || event == eadk_event_right || event == eadk_event_back ||
          event == eadk_event_exe || event == eadk_event_ok) {{
        easter_egg_visible = false;
        grid_mode = easter_return_to_grid;
        if (grid_mode) {{
          show_grid();
        }} else {{
          show_image();
        }}
      }}
      continue;
    }}
    if (event == eadk_event_exe) {{
      grid_mode = true;
      show_grid();
    }} else if (grid_mode) {{
      if (event == eadk_event_ok) {{
        grid_mode = false;
        show_image();
      }} else if (event == eadk_event_right) {{
        current_image = (current_image + 1) % IMAGE_COUNT;
        show_grid();
      }} else if (event == eadk_event_left) {{
        current_image = (current_image + IMAGE_COUNT - 1) % IMAGE_COUNT;
        show_grid();
      }} else if (event == eadk_event_down && current_image + GRID_COLUMNS < IMAGE_COUNT) {{
        current_image += GRID_COLUMNS;
        show_grid();
      }} else if (event == eadk_event_up && current_image >= GRID_COLUMNS) {{
        current_image -= GRID_COLUMNS;
        show_grid();
      }}
    }} else if (event == eadk_event_back) {{
      grid_mode = true;
      show_grid();
    }} else if (event == eadk_event_right) {{
      current_image = (current_image + 1) % IMAGE_COUNT;
      show_image();
    }} else if (event == eadk_event_left) {{
      current_image = (current_image + IMAGE_COUNT - 1) % IMAGE_COUNT;
      show_image();
    }}
  }}
}}
''', encoding="ascii")

    (output / "image_data.S").write_text('''.section .rodata.image_data,"a",%progbits
.balign 2
.global image_data
.type image_data, %object
image_data:
.incbin "images.rgb565"
.size image_data, .-image_data
''', encoding="ascii")
    print(f"\nReady: {count} image(s) ({data_path.stat().st_size:,} pixel-data bytes).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--icon", type=Path, required=True)
    args = parser.parse_args()
    try:
        prepare(args.images, args.output, args.icon)
    except Exception as error:
        print(f"Image preparation failed: {error}", file=sys.stderr)
        raise
