"""The MouthMixer icon (tray and shortcut): a mic on a coloured circle that shows the listener's state."""

from __future__ import annotations

COLOURS = {"paused": (140, 140, 140), "muted": (200, 60, 60), "listening": (60, 130, 230), "capturing": (240, 170, 40)}


def image(state: str = "listening", size: int = 64):
    from PIL import Image, ImageDraw

    s = size / 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4 * s, 4 * s, 60 * s, 60 * s), fill=COLOURS.get(state, COLOURS["listening"]))
    d.rounded_rectangle((25 * s, 14 * s, 39 * s, 38 * s), radius=7 * s, fill=(255, 255, 255))
    d.line((32 * s, 38 * s, 32 * s, 48 * s), fill=(255, 255, 255), width=max(1, int(3 * s)))
    d.line((24 * s, 48 * s, 40 * s, 48 * s), fill=(255, 255, 255), width=max(1, int(3 * s)))
    return img


def write_ico(path: str) -> None:
    image("listening", 256).save(path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])


if __name__ == "__main__":
    import sys

    write_ico(sys.argv[1])
