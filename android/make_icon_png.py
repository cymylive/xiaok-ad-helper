from PIL import Image, ImageDraw
import os

S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([8, 8, S-8, S-8], radius=56, fill=(43, 108, 176, 255))
d.polygon([(S//2, 44), (S//2+46, 110), (S//2-46, 110)], fill=(255, 255, 255, 255))
d.rounded_rectangle([S//2-40, 122, S//2+40, 134], radius=6, fill=(255, 255, 255, 220))
d.polygon([(S//2, 212), (S//2-46, 146), (S//2+46, 146)], fill=(255, 255, 255, 255))

out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "app", "src", "main", "res", "drawable", "ic_launcher.png")
img.save(out)
print("saved", out)
