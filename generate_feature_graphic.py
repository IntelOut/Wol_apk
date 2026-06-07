"""Generate a 1024x500 feature graphic using the actual icon.png."""

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 500
BG = (48, 63, 159)
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
ICON_SIZE = 180


def main():
    bg = Image.new("RGBA", (W, H), BG)
    draw = ImageDraw.Draw(bg)

    icon = Image.open("icon.png").convert("RGBA")
    icon_resized = icon.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)

    ix = (W - ICON_SIZE) // 2
    iy = 60
    bg.paste(icon_resized, (ix, iy), icon_resized)

    try:
        font_title = ImageFont.truetype("arial.ttf", 42)
        font_sub = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    title = "Wake on LAN"
    _, _, tw, th = draw.textbbox((0, 0), title, font=font_title)
    draw.text(
        ((W - tw) // 2, iy + ICON_SIZE + 30),
        title,
        fill=WHITE,
        font=font_title,
    )

    subtitle = "Send magic packets from your phone"
    _, _, sw, _ = draw.textbbox((0, 0), subtitle, font=font_sub)
    draw.text(
        ((W - sw) // 2, iy + ICON_SIZE + 30 + th + 10),
        subtitle,
        fill=GRAY,
        font=font_sub,
    )

    bg.save("feature_graphic.png")
    print("feature_graphic.png regenerated from icon.png (1024x500)")


if __name__ == "__main__":
    main()
