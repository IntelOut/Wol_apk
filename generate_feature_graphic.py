"""Generate a 1024x500 feature graphic for Google Play listing."""

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 500
BG = (48, 63, 159)
ACCENT = (156, 39, 176)
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)


def main():
    img = Image.new("RGBA", (W, H), BG)
    draw = ImageDraw.Draw(img)

    cx, cy = W // 2, H // 2

    box_w, box_h = 380, 160
    x0 = cx - box_w // 2
    y0 = cy - box_h // 2 - 10
    x1 = cx + box_w // 2
    y1 = cy + box_h // 2 - 10

    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=24,
        fill=None,
        outline=WHITE,
        width=10,
    )

    inner = 20
    draw.rounded_rectangle(
        [x0 + inner, y0 + inner, x1 - inner, y1 - inner],
        radius=12,
        fill=WHITE,
        outline=None,
    )

    power_cx, power_cy = cx, (y0 + inner + y1 - inner) // 2
    power_r = 30
    draw.ellipse(
        [power_cx - power_r, power_cy - power_r,
         power_cx + power_r, power_cy + power_r],
        fill=ACCENT,
        outline=None,
    )

    try:
        font_title = ImageFont.truetype("arial.ttf", 36)
        font_sub = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    title = "Wake on LAN"
    _, _, tw, th = draw.textbbox((0, 0), title, font=font_title)
    draw.text(
        ((W - tw) // 2, y1 + 30),
        title,
        fill=WHITE,
        font=font_title,
    )

    subtitle = "Send magic packets from your phone"
    _, _, sw, sh = draw.textbbox((0, 0), subtitle, font=font_sub)
    draw.text(
        ((W - sw) // 2, y1 + 30 + th + 12),
        subtitle,
        fill=GRAY,
        font=font_sub,
    )

    img.save("feature_graphic.png")
    print("feature_graphic.png generated (1024x500)")


if __name__ == "__main__":
    main()
