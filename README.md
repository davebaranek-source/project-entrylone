# Level image renderer

Install the image dependency with `py -m pip install -r requirements.txt` on
Windows (or `python -m pip install -r requirements.txt` elsewhere), then run:

```text
py level_image.py
```

The script prints the sector containing the center of `resources/Level_1.png`.
It detects the green grid and removes its lines; clipped sectors at the edges
are included and stretched to the same size as full sectors. Each sector is
resampled to the existing 96 by 128 subpixel map and displayed as 48 by 32
Unicode cells. A two-colour RGB fit selects each cell's foreground, background,
and quadrant-block or Braille character. Braille dots are an approximation
whose appearance depends on the terminal font.

For other sectors, use `find_sectors`, `convert_sector`, and `format_sector` from
`level_image.py`, or iterate `convert_all_sectors(image)` to convert every
sector in row-major order. Pass an open Pillow image to these functions.
Transparent pixels are composited onto white. The output requires a
Unicode-capable terminal with 24-bit ANSI colour support.

Run the tests with `py -m unittest discover -s tests`.
