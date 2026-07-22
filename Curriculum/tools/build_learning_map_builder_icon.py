"""Build the Student Learning Map Builder application icons."""

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets"
PNG_PATH = ASSET_DIR / "student-learning-map-builder.png"
ICO_PATH = ASSET_DIR / "student-learning-map-builder.ico"

SIZE = 1024
MX_RED = "#CF003D"
INK = "#171717"
WHITE = "#FFFFFF"
PALE_GRAY = "#E8E8E8"


def scaled(value: int) -> int:
    return round(value * SIZE / 256)


def build_icon() -> Image.Image:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (scaled(10), scaled(10), scaled(246), scaled(246)),
        radius=scaled(45),
        fill=INK,
    )
    draw.rounded_rectangle(
        (scaled(49), scaled(29), scaled(207), scaled(227)),
        radius=scaled(18),
        fill=WHITE,
    )
    draw.rounded_rectangle(
        (scaled(49), scaled(29), scaled(207), scaled(71)),
        radius=scaled(18),
        fill=MX_RED,
    )
    draw.rectangle(
        (scaled(49), scaled(51), scaled(207), scaled(71)),
        fill=MX_RED,
    )

    for top in (91, 132, 173):
        box = (scaled(70), scaled(top), scaled(94), scaled(top + 24))
        draw.rounded_rectangle(box, radius=scaled(4), outline=MX_RED, width=scaled(4))
        draw.line(
            (
                scaled(75),
                scaled(top + 12),
                scaled(82),
                scaled(top + 19),
                scaled(92),
                scaled(top + 6),
            ),
            fill=MX_RED,
            width=scaled(4),
            joint="curve",
        )
        draw.rounded_rectangle(
            (scaled(109), scaled(top + 4), scaled(186), scaled(top + 11)),
            radius=scaled(3),
            fill=INK,
        )
        draw.rounded_rectangle(
            (scaled(109), scaled(top + 16), scaled(166), scaled(top + 22)),
            radius=scaled(3),
            fill=PALE_GRAY,
        )

    return image


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    image = build_icon()
    image.save(PNG_PATH, format="PNG", optimize=True)
    image.save(
        ICO_PATH,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Created {PNG_PATH}")
    print(f"Created {ICO_PATH}")


if __name__ == "__main__":
    main()
