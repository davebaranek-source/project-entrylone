import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from level_image import (
    Cell, Sector, _character_for_mask, _fit_cell, center_sector,
    convert_all_sectors, convert_sector, find_sectors, format_sector,
)


class LevelImageTests(unittest.TestCase):
    def test_grid_detection_includes_edges_and_removes_lines(self):
        image = Image.new("RGB", (10, 10), (200, 200, 200))
        draw = ImageDraw.Draw(image)
        draw.line((4, 0, 4, 9), fill=(70, 180, 30))
        draw.line((0, 4, 9, 4), fill=(70, 180, 30))
        sectors = find_sectors(image)
        self.assertEqual([sector.bounds for sector in sectors], [
            (0, 0, 4, 4), (5, 0, 10, 4),
            (0, 5, 4, 10), (5, 5, 10, 10),
        ])
        self.assertEqual(center_sector(image, sectors), sectors[3])

    def test_missing_grid_and_midpoint_on_grid_fail_explicitly(self):
        image = Image.new("RGB", (9, 9), "white")
        with self.assertRaisesRegex(ValueError, "No green sector grid"):
            find_sectors(image)
        draw = ImageDraw.Draw(image)
        draw.line((4, 0, 4, 8), fill=(70, 180, 30))
        draw.line((0, 4, 8, 4), fill=(70, 180, 30))
        with self.assertRaisesRegex(ValueError, "midpoint falls on a grid"):
            center_sector(image, find_sectors(image))

    def test_uniform_color_and_quadrant_mask(self):
        color = (42, 91, 150)
        self.assertEqual(_fit_cell([color] * 8), Cell(" ", color, color))
        self.assertEqual(_character_for_mask(0b00000101), "▘")
        self.assertEqual(_character_for_mask(0b00000001), "⠁")
        self.assertEqual(_character_for_mask(0b10000000), "⢀")

    def test_two_color_partition_reproduces_its_samples(self):
        black, white = (0, 0, 0), (255, 255, 255)
        cell = _fit_cell([white, black, white, black, black, black, black, black])
        self.assertEqual(cell, Cell("▘", white, black))

    def test_conversion_and_format_have_exact_dimensions(self):
        image = Image.new("RGB", (2, 4), (10, 20, 30))
        cells = convert_sector(image, Sector(0, 0, (0, 0, 2, 4)))
        self.assertEqual((len(cells), len(cells[0])), (32, 48))
        self.assertTrue(all(cell.background == (10, 20, 30)
                            for row in cells for cell in row))
        lines = format_sector(cells).splitlines()
        self.assertEqual(len(lines), 32)
        self.assertTrue(all(len(re.sub(r"\x1b\[[0-9;]*m", "", line)) == 48
                            for line in lines))

    def test_all_sectors_are_converted_lazily(self):
        image = Image.new("RGB", (5, 5), (10, 20, 30))
        draw = ImageDraw.Draw(image)
        draw.line((2, 0, 2, 4), fill=(70, 180, 30))
        draw.line((0, 2, 4, 2), fill=(70, 180, 30))
        converted = convert_all_sectors(image)
        sector, cells = next(converted)
        self.assertEqual(sector.bounds, (0, 0, 2, 2))
        self.assertEqual((len(cells), len(cells[0])), (32, 48))
        self.assertEqual(len(list(converted)), 3)

    def test_actual_level_center_sector(self):
        path = Path(__file__).resolve().parents[1] / "resources" / "Level_1.png"
        with Image.open(path) as image:
            sectors = find_sectors(image)
            self.assertEqual(len(sectors), 112)
            sector = center_sector(image, sectors)
            self.assertEqual((sector.row, sector.column), (3, 7))
            self.assertEqual(sector.bounds, (624, 310, 714, 439))
            cells = convert_sector(image, sector)
        self.assertEqual((len(cells), len(cells[0])), (32, 48))
        colors = {cell.background for row in cells for cell in row}
        self.assertGreater(len(colors), 10)

    def test_command_writes_utf8_when_stdout_uses_legacy_encoding(self):
        root = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp1252"
        result = subprocess.run(
            [sys.executable, str(root / "level_image.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            check=True,
        )
        lines = result.stdout.decode("utf-8").splitlines()
        self.assertEqual(len(lines), 32)
        self.assertTrue(all(len(re.sub(r"\x1b\[[0-9;]*m", "", line)) == 48
                            for line in lines))


if __name__ == "__main__":
    unittest.main()
