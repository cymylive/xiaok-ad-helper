from PIL import Image, ImageDraw

S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([8, 8, S-8, S-8], radius=56, fill=(43, 108, 176, 255))
# 上箭头
d.polygon([(S//2, 44), (S//2+46, 110), (S//2-46, 110)], fill=(255, 255, 255, 255))
# 中间横条（鼠标轮廓感）
d.rounded_rectangle([S//2-40, 122, S//2+40, 134], radius=6, fill=(255, 255, 255, 220))
# 下箭头
d.polygon([(S//2, 212), (S//2-46, 146), (S//2+46, 146)], fill=(255, 255, 255, 255))
img.save("icon.ico", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print("icon.ico created")
