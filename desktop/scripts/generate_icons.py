from pathlib import Path
from PIL import Image, ImageDraw

out = Path(__file__).resolve().parents[1] / "electron" / "resources"
out.mkdir(parents=True, exist_ok=True)

for name, size in (("icon.png", 256), ("tray-icon.png", 32)):
    image = Image.new("RGBA", (size, size), (11, 16, 19, 0))
    draw = ImageDraw.Draw(image)
    margin = max(2, size // 10)
    draw.rounded_rectangle((margin, margin, size - margin, size - margin), radius=size // 5, fill=(14, 40, 44, 255), outline=(83, 216, 209, 255), width=max(1, size // 32))
    points = [(size * .31, size * .55), (size * .56, size * .18), (size * .49, size * .45), (size * .69, size * .45), (size * .39, size * .83), (size * .47, size * .55)]
    draw.polygon(points, fill=(83, 216, 209, 255))
    draw.ellipse((size * .67, size * .65, size * .84, size * .82), fill=(242, 184, 75, 255))
    image.save(out / name)
