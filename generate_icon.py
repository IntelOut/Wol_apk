"""Generate a 512x512 app icon — bold, centered, no small details."""

from PIL import Image, ImageDraw

SIZE = 512
MARGIN = 40
BG = (48, 63, 159)
ACCENT = (156, 39, 176)
WHITE = (255, 255, 255)


def main():
    img = Image.new("RGBA", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)

    m = MARGIN
    cw = SIZE - 2 * m
    ch = int(cw * 0.72)

    cx, cy = SIZE // 2, SIZE // 2

    x0 = cx - cw // 2
    y0 = cy - ch // 2 - 10
    x1 = cx + cw // 2
    y1 = cy + ch // 2 - 10

    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=24,
        fill=None,
        outline=WHITE,
        width=14,
    )

    inner = 28
    draw.rounded_rectangle(
        [x0 + inner, y0 + inner, x1 - inner, y1 - inner],
        radius=12,
        fill=WHITE,
        outline=None,
    )

    power_cx, power_cy = cx, (y0 + inner + y1 - inner) // 2
    power_r = 44
    draw.ellipse(
        [
            power_cx - power_r,
            power_cy - power_r,
            power_cx + power_r,
            power_cy + power_r,
        ],
        fill=ACCENT,
        outline=None,
    )

    stand_w = 24
    stand_h = 36
    sx0 = cx - stand_w // 2
    sx1 = cx + stand_w // 2
    sy0 = y1
    sy1 = y1 + stand_h
    draw.rectangle([sx0, sy0, sx1, sy1], fill=WHITE)

    base_w = 120
    base_h = 16
    bx0 = cx - base_w // 2
    bx1 = cx + base_w // 2
    by0 = sy1
    by1 = sy1 + base_h
    draw.rounded_rectangle(
        [bx0, by0, bx1, by1],
        radius=8,
        fill=WHITE,
    )

    img.save("icon.png")
    print("icon.png regenerated (512x512)")


if __name__ == "__main__":
    main()
