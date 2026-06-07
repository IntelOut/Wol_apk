"""Generate a 1024x500 feature graphic matching the app icon style."""

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 500
BG = (48, 63, 159)
ACCENT = (156, 39, 176)
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)


def main():
    img = Image.new("RGBA", (W, H), BG)
    draw = ImageDraw.Draw(img)

    cx, cy = W // 2, 220

    cw = 200
    ch = int(cw * 0.72)
    x0 = cx - cw // 2
    y0 = cy - ch // 2
    x1 = cx + cw // 2
    y1 = cy + ch // 2

    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=16,
        fill=None,
        outline=WHITE,
        width=8,
    )

    inner = 18
    draw.rounded_rectangle(
        [x0 + inner, y0 + inner, x1 - inner, y1 - inner],
        radius=8,
        fill=WHITE,
        outline=None,
    )

    power_cx, power_cy = cx, (y0 + inner + y1 - inner) // 2
    power_r = 28
    draw.ellipse(
        [power_cx - power_r, power_cy - power_r,
         power_cx + power_r, power_cy + power_r],
        fill=ACCENT,
        outline=None,
    )

    stand_w = 14
    stand_h = 22
    sx0 = cx - stand_w // 2
    sx1 = cx + stand_w // 2
    sy0 = y1
    sy1 = y1 + stand_h
    draw.rectangle([sx0, sy0, sx1, sy1], fill=WHITE)

    base_w = 80
    base_h = 10
    bx0 = cx - base_w // 2
    bx1 = cx + base_w // 2
    by0 = sy1
    by1 = sy1 + base_h
    draw.rounded_rectangle(
        [bx0, by0, bx1, by1],
        radius=5,
        fill=WHITE,
    )

    try:
        font_title = ImageFont.truetype("arial.ttf", 40)
        font_sub = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    title = "Wake on LAN"
    _, _, tw, th = draw.textbbox((0, 0), title, font=font_title)
    draw.text(
        ((W - tw) // 2, sy1 + 30),
        title,
        fill=WHITE,
        font=font_title,
    )

    subtitle = "Send magic packets from your phone"
    _, _, sw, _ = draw.textbbox((0, 0), subtitle, font=font_sub)
    draw.text(
        ((W - sw) // 2, sy1 + 30 + th + 8),
        subtitle,
        fill=GRAY,
        font=font_sub,
    )

    img.save("feature_graphic.png")
    print("feature_graphic.png regenerated (1024x500) matching icon style")


if __name__ == "__main__":
    main()
