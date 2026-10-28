"""Convert the green-grid level image into true-colour terminal sectors."""

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterator

from PIL import Image


MAP_WIDTH = 96
MAP_HEIGHT = 128
CELL_WIDTH = 2
CELL_HEIGHT = 4
BRAILLE_WEIGHTS = (1, 8, 2, 16, 4, 32, 64, 128)
QUADRANT_CHARACTERS = (
    " ", "▘", "▝", "▀", "▖", "▌", "▞", "▛",
    "▗", "▚", "▐", "▜", "▄", "▙", "▟", "█",
)

Color = tuple[int, int, int]


@dataclass(frozen=True)
class Sector:
    row: int
    column: int
    # Pillow crop coordinates: left/top inclusive, right/bottom exclusive.
    bounds: tuple[int, int, int, int]


@dataclass(frozen=True)
class Cell:
    character: str
    foreground: Color
    background: Color


def _is_grid_green(color: Color) -> bool:
    r, g, b = color
    return g >= 150 and g - r >= 50 and g - b >= 40 and r <= 140


def _content_intervals(counts: list[int], cross_size: int) -> list[tuple[int, int]]:
    """Return image intervals between full-length green grid-line bands."""
    lines = [count * 2 > cross_size for count in counts]
    if not any(lines):
        raise ValueError("No green sector grid was detected in the level image")

    intervals = []
    start = 0
    for position, is_line in enumerate(lines):
        if is_line:
            if start < position:
                intervals.append((start, position))
            start = position + 1
    if start < len(lines):
        intervals.append((start, len(lines)))
    if not intervals:
        raise ValueError("The grid leaves no image content to render")
    return intervals


def find_sectors(image: Image.Image) -> list[Sector]:
    """Find all grid rectangles, including clipped rectangles at image edges."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    if not width or not height:
        raise ValueError("The level image is empty")
    columns = [0] * width
    rows = [0] * height
    pixels = rgb.load()
    for y in range(height):
        for x in range(width):
            if _is_grid_green(pixels[x, y]):
                columns[x] += 1
                rows[y] += 1

    x_intervals = _content_intervals(columns, height)
    y_intervals = _content_intervals(rows, width)
    return [
        Sector(row, column, (left, top, right, bottom))
        for row, (top, bottom) in enumerate(y_intervals)
        for column, (left, right) in enumerate(x_intervals)
    ]


def center_sector(image: Image.Image, sectors: list[Sector]) -> Sector:
    """Choose the sector containing the image midpoint."""
    x, y = image.width // 2, image.height // 2
    for sector in sectors:
        left, top, right, bottom = sector.bounds
        if left <= x < right and top <= y < bottom:
            return sector
    raise ValueError("The image midpoint falls on a grid line, not in a sector")


def _character_for_mask(mask: int) -> str:
    # Prefer solid quadrant blocks when the 2x4 mask permits them.
    quadrants = ((0, 2), (1, 3), (4, 6), (5, 7))
    quadrant_mask = 0
    for quadrant, (first, second) in enumerate(quadrants):
        first_set = bool(mask & (1 << first))
        if first_set != bool(mask & (1 << second)):
            break
        if first_set:
            quadrant_mask |= 1 << quadrant
    else:
        return QUADRANT_CHARACTERS[quadrant_mask]

    braille_mask = sum(weight for bit, weight in enumerate(BRAILLE_WEIGHTS)
                       if mask & (1 << bit))
    return chr(0x2800 + braille_mask)


def _fit_cell(pixels: list[Color]) -> Cell:
    """Find the least-squared-error two-colour partition of eight RGB pixels."""
    if len(pixels) != 8:
        raise ValueError("A terminal cell must contain exactly eight pixels")

    totals = tuple(sum(pixel[channel] for pixel in pixels) for channel in range(3))
    # A mask and its complement describe the same partition.
    sums = [(0, 0, 0)] * 128
    counts = [0] * 128
    best_mask = 0
    best_score = sum(value * value for value in totals) / 8
    for mask in range(1, 128):
        bit = mask & -mask
        index = bit.bit_length() - 1
        previous = mask ^ bit
        count = counts[previous] + 1
        counts[mask] = count
        red, green, blue = sums[previous]
        pixel = pixels[index]
        color_sum = (red + pixel[0], green + pixel[1], blue + pixel[2])
        sums[mask] = color_sum
        score = sum(
            value * value / count + (total - value) ** 2 / (8 - count)
            for value, total in zip(color_sum, totals)
        )
        if score > best_score:
            best_score = score
            best_mask = mask

    if best_mask == 0:
        color = tuple(round(value / 8) for value in totals)
        return Cell(" ", color, color)

    count = counts[best_mask]
    color_sum = sums[best_mask]
    foreground = tuple(round(value / count) for value in color_sum)
    background = tuple(round((total - value) / (8 - count))
                       for value, total in zip(color_sum, totals))
    # Keep the more common colour in the background.
    if count > 4:
        best_mask ^= 255
        foreground, background = background, foreground
    return Cell(_character_for_mask(best_mask), foreground, background)


def convert_sector(image: Image.Image, sector: Sector) -> list[list[Cell]]:
    """Convert one sector to 32 rows of 48 cells, representing 96x128 pixels."""
    left, top, right, bottom = sector.bounds
    if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
        raise ValueError(f"Sector bounds are outside the image: {sector.bounds}")
    rgba = image.crop(sector.bounds).convert("RGBA")
    white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    rgb = Image.alpha_composite(white, rgba).convert("RGB")
    bitmap = rgb.resize((MAP_WIDTH, MAP_HEIGHT), Image.Resampling.LANCZOS)
    pixels = bitmap.load()
    return [
        [
            _fit_cell([
                pixels[x + dx, y + dy]
                for dy in range(CELL_HEIGHT)
                for dx in range(CELL_WIDTH)
            ])
            for x in range(0, MAP_WIDTH, CELL_WIDTH)
        ]
        for y in range(0, MAP_HEIGHT, CELL_HEIGHT)
    ]


def convert_all_sectors(image: Image.Image) -> Iterator[tuple[Sector, list[list[Cell]]]]:
    """Yield every converted sector in row-major order, without retaining them all."""
    for sector in find_sectors(image):
        yield sector, convert_sector(image, sector)


def format_sector(cells: list[list[Cell]]) -> str:
    """Format terminal cells with RGB foreground and background ANSI colours."""
    lines = []
    for row in cells:
        parts = []
        for cell in row:
            r, g, b = cell.foreground
            br, bg, bb = cell.background
            parts.append(
                f"\x1b[38;2;{r};{g};{b}m"
                f"\x1b[48;2;{br};{bg};{bb}m{cell.character}"
            )
        lines.append("".join(parts) + "\x1b[0m")
    return "\n".join(lines)


def main() -> None:
    image_path = Path(__file__).resolve().parent / "resources" / "Level_1.png"
    with Image.open(image_path) as image:
        sector = center_sector(image, find_sectors(image))
        rendered = format_sector(convert_sector(image, sector))
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(rendered + "\n")


if __name__ == "__main__":
    main()
